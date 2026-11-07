#include "metrics.h"

#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QLocale>
#include <QProcess>
#include <QRegularExpression>
#include <QSet>
#include <QSysInfo>
#include <QThread>

#include <algorithm>
#include <cmath>
#include <sys/statvfs.h>
#include <unistd.h>

namespace {

const int kHistory = 90;  // ninety samples, so ninety seconds at the default rate

QByteArray readBytes(const QString &path)
{
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly))
        return {};
    return file.readAll();
}

QString readText(const QString &path)
{
    return QString::fromUtf8(readBytes(path)).trimmed();
}

double readNumber(const QString &path)
{
    bool ok = false;
    const double value = readText(path).toDouble(&ok);
    return ok ? value : 0.0;
}

// Every hwmon chip whose name file is what we are after. A machine can have
// several (one per GPU, one per NVMe), so this returns a list.
QStringList hwmonPaths(const QString &name)
{
    QStringList paths;
    const auto entries = QDir("/sys/class/hwmon").entryList(QDir::Dirs | QDir::NoDotAndDotDot, QDir::Name);
    for (const auto &entry : entries) {
        const QString path = "/sys/class/hwmon/" + entry;
        if (readText(path + "/name") == name)
            paths << path;
    }
    return paths;
}

struct Reading {
    QString label;
    double value = 0;
};

// tempN_input and its tempN_label, in degrees Celsius.
QList<Reading> temperatures(const QString &chip)
{
    QList<Reading> readings;
    const auto entries = QDir(chip).entryList({"temp*_input"}, QDir::Files, QDir::Name);
    for (const auto &entry : entries) {
        const QString input = chip + "/" + entry;
        const QString label = readText(chip + "/" + QString(entry).replace("_input", "_label"));
        readings << Reading{label, readNumber(input) / 1000.0};
    }
    return readings;
}

// The first reading whose label contains one of the wanted names, in order.
double pickTemperature(const QList<Reading> &readings, const QStringList &labels, double fallback = 0)
{
    for (const auto &label : labels)
        for (const auto &reading : readings)
            if (reading.label.contains(label, Qt::CaseInsensitive))
                return reading.value;
    return fallback;
}

QString number(double value, int decimals = 0)
{
    return QLocale().toString(value, 'f', decimals);
}

QString percentText(double value)
{
    return number(value) + "%";
}

QString temperatureText(double celsius)
{
    if (celsius <= 0)
        return QStringLiteral("–");
    return number(celsius) + QStringLiteral("°C");
}

QString frequencyText(double megahertz)
{
    if (megahertz <= 0)
        return QStringLiteral("–");
    if (megahertz >= 1000)
        return number(megahertz / 1000.0, 1) + QStringLiteral(" GHz");
    return number(megahertz) + QStringLiteral(" MHz");
}

// The kernel only exposes PCI ids, so the model name comes from lspci when it
// is installed. Without it the vendor is still known, which beats inventing a
// name for the card.
QString gpuName(const QString &device)
{
    const QString bdf = QFileInfo(device).canonicalFilePath().section('/', -1);
    if (!bdf.isEmpty()) {
        QProcess lspci;
        lspci.start("lspci", {"-s", bdf, "-mm"});
        if (lspci.waitForFinished(800) && lspci.exitCode() == 0) {
            const QString output = QString::fromUtf8(lspci.readAllStandardOutput()).trimmed();
            const QRegularExpression quoted("\"([^\"]*)\"");
            QStringList fields;
            auto it = quoted.globalMatch(output);
            while (it.hasNext())
                fields << it.next().captured(1);
            if (fields.size() >= 3)
                return fields.at(2);
            if (fields.size() == 2)
                return fields.at(1);
        }
    }

    const QString vendor = readText(device + "/vendor");
    if (vendor == "0x1002")
        return QStringLiteral("AMD Radeon");
    if (vendor == "0x10de")
        return QStringLiteral("NVIDIA GeForce");
    if (vendor == "0x8086")
        return QStringLiteral("Intel Graphics");
    return QStringLiteral("GPU");
}

// A whole disk, as opposed to a partition or a mapper volume, so the I/O rate
// is counted once per drive.
bool isWholeDisk(const QString &name)
{
    static const QRegularExpression pattern("^(sd[a-z]+|hd[a-z]+|vd[a-z]+|nvme\\d+n\\d+|mmcblk\\d+)$");
    return pattern.match(name).hasMatch();
}

bool isRealFilesystem(const QString &type)
{
    static const QStringList pseudo = {
        "proc", "sysfs", "devtmpfs", "devpts", "tmpfs", "ramfs", "overlay", "squashfs",
        "cgroup", "cgroup2", "securityfs", "debugfs", "tracefs", "configfs", "fusectl",
        "mqueue", "hugetlbfs", "pstore", "bpf", "autofs", "binfmt_misc", "efivarfs",
        "nsfs", "rpc_pipefs", "fuse.gvfsd-fuse", "fuse.portal", "fuse.archivemount",
    };
    return !pseudo.contains(type);
}

// /proc/mounts escapes spaces and the like as octal.
QString unescapeMount(const QString &value)
{
    QString result;
    for (int i = 0; i < value.size(); ++i) {
        if (value.at(i) == '\\' && i + 3 < value.size()) {
            result += QChar(value.mid(i + 1, 3).toInt(nullptr, 8));
            i += 3;
        } else {
            result += value.at(i);
        }
    }
    return result;
}

}  // namespace

qint64 CpuTimes::total() const
{
    qint64 sum = 0;
    for (qint64 value : values)
        sum += value;
    return sum;
}

qint64 CpuTimes::idle() const
{
    // iowait counts as idle: the core was not running anything.
    return values[3] + values[4];
}

Metrics::Metrics()
{
    // The CPU model and the GPU never change, so resolve them once.
    const auto info = readText("/proc/cpuinfo").split('\n');
    for (const auto &line : info)
        if (line.startsWith("model name")) {
            m_cpuModel = line.section(':', 1).trimmed();
            break;
        }
    findGpu();
}

void Metrics::findGpu()
{
    // The card with the most VRAM is the discrete one, which is the one people
    // mean when they ask about the GPU. Integrated and discrete both work; the
    // same files exist either way.
    static const QRegularExpression cardPattern("^card\\d+$");
    double bestVram = -1;
    const auto entries = QDir("/sys/class/drm").entryList(QDir::Dirs | QDir::NoDotAndDotDot, QDir::Name);
    for (const auto &entry : entries) {
        if (!cardPattern.match(entry).hasMatch())
            continue;
        const QString device = "/sys/class/drm/" + entry + "/device";
        const double vram = readNumber(device + "/mem_info_vram_total");
        if (vram > bestVram) {
            bestVram = vram;
            m_gpuDevice = device;
        }
    }
    if (m_gpuDevice.isEmpty())
        return;

    const auto chips = QDir(m_gpuDevice + "/hwmon").entryList({"hwmon*"}, QDir::Dirs | QDir::NoDotAndDotDot, QDir::Name);
    if (!chips.isEmpty())
        m_gpuHwmon = m_gpuDevice + "/hwmon/" + chips.first();
    m_gpuName = gpuName(m_gpuDevice);
}

void Metrics::sample()
{
    const qint64 now = QDateTime::currentMSecsSinceEpoch();
    const bool first = m_lastSample == 0;
    double seconds = first ? 0 : (now - m_lastSample) / 1000.0;
    if (seconds < 0.001)
        seconds = 0;
    m_lastSample = now;

    sampleCpu();
    sampleMemory();
    sampleGpu();
    sampleDisks(seconds);
    sampleNetwork(seconds);
    sampleProcesses(seconds);
    sampleSystem();

    // The first reading only sets the baselines, so its rates are meaningless
    // and must not become a dip at the start of a chart.
    if (first)
        return;
    push(m_cpuHistory, m_cpuUsage);
    push(m_gpuHistory, m_gpuUsage);
    push(m_networkIn, m_netInRate);
    push(m_networkOut, m_netOutRate);
    push(m_memoryHistory, m_memoryPercent);
    push(m_ioReadHistory, m_ioReadRate);
    push(m_ioWriteHistory, m_ioWriteRate);
}

void Metrics::resetBaselines()
{
    m_lastSample = 0;
    m_hasCpu = false;
    m_hasIo = false;
    m_previousCores.clear();
    m_previousNetwork.clear();
    m_previousProcessTicks.clear();
}

void Metrics::push(QVariantList &history, double value)
{
    history << value;
    while (history.size() > kHistory)
        history.removeFirst();
}

void Metrics::sampleCpu()
{
    CpuTimes total;
    QList<CpuTimes> cores;
    const auto lines = readBytes("/proc/stat").split('\n');
    for (const auto &line : lines) {
        if (!line.startsWith("cpu"))
            continue;
        if (line.size() > 3 && line.at(3) == ' ')
            total = parseCpuLine(line);
        else
            cores << parseCpuLine(line);
    }

    m_cpuUsage = m_hasCpu ? usagePercent(m_previousTotal, total) : 0;

    QVariantList coreUsage;
    coreUsage.reserve(cores.size());
    for (int i = 0; i < cores.size(); ++i) {
        const bool known = i < m_previousCores.size();
        coreUsage << (known ? usagePercent(m_previousCores.at(i), cores.at(i)) : 0.0);
    }

    m_previousTotal = total;
    m_previousCores = cores;
    m_hasCpu = true;

    // Average clock over the cores that report one.
    double sum = 0;
    int count = 0;
    const auto cpus = QDir("/sys/devices/system/cpu").entryList({"cpu[0-9]*"}, QDir::Dirs, QDir::Name);
    for (const auto &cpu : cpus) {
        const double kilohertz = readNumber("/sys/devices/system/cpu/" + cpu + "/cpufreq/scaling_cur_freq");
        if (kilohertz > 0) {
            sum += kilohertz / 1000.0;
            ++count;
        }
    }
    const double megahertz = count ? sum / count : 0;

    // k10temp (AMD), coretemp (Intel), zenpower (a third-party AMD driver).
    double temperature = 0;
    for (const auto &name : {"k10temp", "coretemp", "zenpower"}) {
        const auto chips = hwmonPaths(name);
        if (chips.isEmpty())
            continue;
        const auto readings = temperatures(chips.first());
        temperature = pickTemperature(readings, {"Tctl", "Package", "Tdie"}, readings.isEmpty() ? 0 : readings.first().value);
        if (temperature > 0)
            break;
    }

    QVariantMap cpu;
    cpu["usage"] = m_cpuUsage;
    cpu["usageText"] = percentText(m_cpuUsage);
    cpu["cores"] = cores.size();
    cpu["coreUsage"] = coreUsage;
    cpu["model"] = m_cpuModel;
    cpu["clock"] = megahertz;
    cpu["clockText"] = frequencyText(megahertz);
    cpu["temp"] = temperature;
    cpu["tempText"] = temperatureText(temperature);
    m_cpu = cpu;
}

void Metrics::sampleMemory()
{
    const auto values = parseMeminfo(readBytes("/proc/meminfo"));
    const double total = values.value("MemTotal");
    const double available = values.value("MemAvailable");
    const double swapTotal = values.value("SwapTotal");
    const double swapFree = values.value("SwapFree");
    const double used = qMax(0.0, total - available);
    const double swapUsed = qMax(0.0, swapTotal - swapFree);

    QVariantMap memory;
    memory["total"] = total;
    memory["used"] = used;
    memory["free"] = qMax(0.0, available);
    memory["percent"] = total > 0 ? used / total * 100.0 : 0;
    memory["usedText"] = humanBytes(used);
    memory["totalText"] = humanBytes(total);
    memory["freeText"] = humanBytes(available);
    memory["percentText"] = percentText(total > 0 ? used / total * 100.0 : 0);
    memory["swapTotal"] = swapTotal;
    memory["swapUsed"] = swapUsed;
    memory["swapPercent"] = swapTotal > 0 ? swapUsed / swapTotal * 100.0 : 0;
    memory["swapUsedText"] = humanBytes(swapUsed);
    memory["swapTotalText"] = humanBytes(swapTotal);
    m_memory = memory;
    m_memoryPercent = memory.value("percent").toDouble();
}

void Metrics::sampleGpu()
{
    QVariantMap gpu;
    if (m_gpuDevice.isEmpty()) {
        gpu["present"] = false;
        m_gpu = gpu;
        m_gpuUsage = 0;
        return;
    }

    const double used = readNumber(m_gpuDevice + "/mem_info_vram_used");
    const double total = readNumber(m_gpuDevice + "/mem_info_vram_total");

    double edge = 0, junction = 0, memory = 0;
    double power = 0, fan = 0;
    bool hasFan = false, hasPower = false;
    if (!m_gpuHwmon.isEmpty()) {
        const auto readings = temperatures(m_gpuHwmon);
        edge = pickTemperature(readings, {"edge"});
        junction = pickTemperature(readings, {"junction", "hotspot"});
        memory = pickTemperature(readings, {"mem", "vram"});
        // microWatts on amdgpu; power1_input is the same unit when averaged is
        // not offered.
        // power1_average is what the card is drawing now; power1_input is the
        // older name for the same thing in microwatts.
        if (QFile::exists(m_gpuHwmon + "/power1_average")) {
            hasPower = true;
            power = readNumber(m_gpuHwmon + "/power1_average") / 1000000.0;
        } else if (QFile::exists(m_gpuHwmon + "/power1_input")) {
            hasPower = true;
            power = readNumber(m_gpuHwmon + "/power1_input") / 1000000.0;
        }

        // A fan at rest reports 0 RPM, which is not the same as a card without
        // one, so presence is a file question rather than a value question.
        if (QFile::exists(m_gpuHwmon + "/fan1_input")) {
            hasFan = true;
            fan = readNumber(m_gpuHwmon + "/fan1_input");
        }
    }

    const double clock = parseClock(readBytes(m_gpuDevice + "/pp_dpm_sclk"));
    const double busy = readNumber(m_gpuDevice + "/gpu_busy_percent");
    m_gpuUsage = qBound(0.0, busy, 100.0);

    gpu["present"] = true;
    gpu["name"] = m_gpuName;
    gpu["usage"] = m_gpuUsage;
    gpu["usageText"] = percentText(m_gpuUsage);
    gpu["vramUsed"] = used;
    gpu["vramTotal"] = total;
    gpu["vramPercent"] = total > 0 ? used / total * 100.0 : 0;
    gpu["vramUsedText"] = humanBytes(used);
    gpu["vramTotalText"] = humanBytes(total);
    gpu["temp"] = edge;
    gpu["tempText"] = temperatureText(edge);
    gpu["junctionText"] = temperatureText(junction);
    gpu["memoryTempText"] = temperatureText(memory);
    gpu["power"] = power;
    gpu["powerText"] = hasPower ? number(power) + " W" : QStringLiteral("–");
    gpu["fan"] = fan;
    gpu["fanText"] = hasFan ? number(fan) + " RPM" : QStringLiteral("–");
    gpu["clock"] = clock;
    gpu["clockText"] = frequencyText(clock);
    m_gpu = gpu;
}

void Metrics::sampleDisks(double seconds)
{
    // Per-drive I/O, read before the mount list so a card can show both.
    quint64 read = 0, written = 0;
    const auto lines = readBytes("/proc/diskstats").split('\n');
    for (const auto &line : lines) {
        const auto fields = QString::fromUtf8(line).trimmed().split(' ', Qt::SkipEmptyParts);
        if (fields.size() < 10 || !isWholeDisk(fields.at(2)))
            continue;
        read += fields.at(5).toULongLong() * 512;
        written += fields.at(9).toULongLong() * 512;
    }

    if (m_hasIo && seconds > 0) {
        m_io["read"] = (read - m_previousRead) / seconds;
        m_io["write"] = (written - m_previousWritten) / seconds;
    } else {
        m_io["read"] = 0.0;
        m_io["write"] = 0.0;
    }
    m_ioReadRate = m_io.value("read").toDouble();
    m_ioWriteRate = m_io.value("write").toDouble();
    m_io["readText"] = humanRate(m_io.value("read").toDouble());
    m_io["writeText"] = humanRate(m_io.value("write").toDouble());
    m_previousRead = read;
    m_previousWritten = written;
    m_hasIo = true;

    // One row per real filesystem, keyed by device so btrfs subvolumes and bind
    // mounts of the same drive do not each take a row.
    struct Disk {
        QString label;
        QString type;
        QString device;
        double total = 0;
        double used = 0;
    };
    QList<Disk> disks;
    QSet<QString> devices;
    const auto mounts = readBytes("/proc/mounts").split('\n');
    for (const auto &line : mounts) {
        const auto fields = QString::fromUtf8(line).split(' ');
        if (fields.size() < 3)
            continue;
        const QString device = unescapeMount(fields.at(0));
        const QString point = unescapeMount(fields.at(1));
        const QString type = fields.at(2);
        if (!device.startsWith('/') || !isRealFilesystem(type) || devices.contains(device))
            continue;

        struct statvfs vfs;
        if (statvfs(point.toUtf8().constData(), &vfs) != 0)
            continue;
        const double fragment = vfs.f_frsize > 0 ? vfs.f_frsize : vfs.f_bsize;
        const double total = vfs.f_blocks * fragment;
        const double free = vfs.f_bfree * fragment;
        if (total < 1024.0 * 1024.0)
            continue;

        devices.insert(device);
        disks << Disk{point, type, device, total, qMax(0.0, total - free)};
    }
    std::sort(disks.begin(), disks.end(), [](const Disk &a, const Disk &b) {
        if (a.label == "/")
            return true;
        if (b.label == "/")
            return false;
        return a.label < b.label;
    });

    QVariantList list;
    for (int i = 0; i < disks.size() && i < 5; ++i) {
        const auto &disk = disks.at(i);
        QVariantMap entry;
        entry["label"] = disk.label;
        entry["type"] = disk.type;
        entry["device"] = disk.device;
        entry["total"] = disk.total;
        entry["used"] = disk.used;
        entry["percent"] = disk.total > 0 ? disk.used / disk.total * 100.0 : 0;
        entry["usedText"] = humanBytes(disk.used);
        entry["totalText"] = humanBytes(disk.total);
        list << entry;
    }
    m_disks = list;

    // The NVMe reports its own temperature, so show it beside the I/O rate when
    // the drive offers one.
    double nvme = 0;
    const auto chips = hwmonPaths("nvme");
    if (!chips.isEmpty()) {
        const auto readings = temperatures(chips.first());
        nvme = pickTemperature(readings, {"Composite"}, readings.isEmpty() ? 0 : readings.first().value);
    }
    m_io["nvmeTempText"] = temperatureText(nvme);
}

void Metrics::sampleNetwork(double seconds)
{
    QHash<QString, QPair<quint64, quint64>> current;  // name -> (received, sent)
    const auto lines = readBytes("/proc/net/dev").split('\n');
    for (const auto &line : lines) {
        const int colon = line.indexOf(':');
        if (colon < 0)
            continue;
        const QString name = QString::fromUtf8(line.left(colon)).trimmed();
        if (name == "lo")
            continue;
        const auto fields = QString::fromUtf8(line.mid(colon + 1)).trimmed().split(QRegularExpression("\\s+"));
        if (fields.size() < 10)
            continue;
        current.insert(name, {fields.at(0).toULongLong(), fields.at(8).toULongLong()});
    }

    struct Interface {
        QString name;
        double received = 0;
        double sent = 0;
        quint64 total = 0;
    };
    QList<Interface> interfaces;
    double received = 0, sent = 0;
    for (auto it = current.begin(); it != current.end(); ++it) {
        const auto previous = m_previousNetwork.value(it.key());
        const double in = seconds > 0 ? qMax<qint64>(0, qint64(it.value().first) - qint64(previous.first)) / seconds : 0;
        const double out = seconds > 0 ? qMax<qint64>(0, qint64(it.value().second) - qint64(previous.second)) / seconds : 0;
        received += in;
        sent += out;
        interfaces << Interface{it.key(), in, out, it.value().first + it.value().second};
    }
    std::sort(interfaces.begin(), interfaces.end(), [](const Interface &a, const Interface &b) {
        if (a.received + a.sent != b.received + b.sent)
            return a.received + a.sent > b.received + b.sent;
        return a.total > b.total;
    });

    QVariantList list;
    for (int i = 0; i < interfaces.size() && i < 4; ++i) {
        const auto &interface = interfaces.at(i);
        QVariantMap entry;
        entry["name"] = interface.name;
        entry["in"] = interface.received;
        entry["out"] = interface.sent;
        entry["inText"] = humanRate(interface.received);
        entry["outText"] = humanRate(interface.sent);
        list << entry;
    }

    m_networks = list;
    m_netInRate = received;
    m_netOutRate = sent;
    m_previousNetwork = current;

    QVariantMap network;
    network["in"] = received;
    network["out"] = sent;
    network["inText"] = humanRate(received);
    network["outText"] = humanRate(sent);
    m_network = network;
}

void Metrics::sampleProcesses(double seconds)
{
    const double hertz = sysconf(_SC_CLK_TCK) > 0 ? double(sysconf(_SC_CLK_TCK)) : 100.0;
    const double pageSize = sysconf(_SC_PAGESIZE) > 0 ? double(sysconf(_SC_PAGESIZE)) : 4096.0;

    struct Row {
        QString name;
        double cpu;
        double memory;
    };
    QHash<QString, Row> grouped;
    QHash<int, double> ticks;

    const auto entries = QDir("/proc").entryList(QDir::Dirs | QDir::NoDotAndDotDot, QDir::Name);
    for (const auto &entry : entries) {
        bool numeric = false;
        const int pid = entry.toInt(&numeric);
        if (!numeric)
            continue;
        ProcessSample sample;
        if (!parseProcessStat(readBytes("/proc/" + entry + "/stat"), sample))
            continue;
        // Kernel threads have no memory of their own, so they are noise here.
        if (sample.rss <= 0)
            continue;

        const double previous = m_previousProcessTicks.value(pid, sample.ticks);
        const double delta = qMax(0.0, sample.ticks - previous);
        const double cpu = seconds > 0 ? delta / hertz / seconds * 100.0 : 0;
        ticks.insert(pid, sample.ticks);

        Row &row = grouped[sample.name];
        row.name = sample.name;
        row.cpu += cpu;
        row.memory += sample.rss * pageSize;
    }
    m_previousProcessTicks = ticks;

    QList<Row> rows = grouped.values();
    std::sort(rows.begin(), rows.end(), [](const Row &a, const Row &b) {
        if (a.cpu != b.cpu)
            return a.cpu > b.cpu;
        return a.memory > b.memory;
    });

    QVariantList list;
    for (int i = 0; i < rows.size() && i < 8; ++i) {
        const auto &row = rows.at(i);
        QVariantMap entry;
        entry["name"] = row.name;
        entry["cpu"] = row.cpu;
        entry["cpuText"] = QLocale().toString(row.cpu, 'f', row.cpu < 10 ? 1 : 0) + "%";
        entry["memory"] = row.memory;
        entry["memoryText"] = humanBytes(row.memory);
        list << entry;
    }
    m_processes = list;
}

void Metrics::sampleSystem()
{
    double uptime = 0;
    const auto uptimeFields = readText("/proc/uptime").split(' ', Qt::SkipEmptyParts);
    if (!uptimeFields.isEmpty())
        uptime = uptimeFields.first().toDouble();

    const auto load = readText("/proc/loadavg").split(' ', Qt::SkipEmptyParts);
    const QString loadText = load.size() >= 3
        ? QStringLiteral("%1 %2 %3")
              .arg(QLocale().toString(load.at(0).toDouble(), 'f', 2),
                   QLocale().toString(load.at(1).toDouble(), 'f', 2),
                   QLocale().toString(load.at(2).toDouble(), 'f', 2))
        : QStringLiteral("–");

    int processCount = 0;
    const auto entries = QDir("/proc").entryList(QDir::Dirs | QDir::NoDotAndDotDot, QDir::Name);
    for (const auto &entry : entries) {
        bool numeric = false;
        entry.toInt(&numeric);
        if (numeric)
            ++processCount;
    }

    QVariantMap system;
    system["hostname"] = QSysInfo::machineHostName();
    system["kernel"] = QSysInfo::kernelVersion();
    system["cpuModel"] = m_cpuModel;
    system["uptime"] = uptime;
    system["uptimeText"] = durationText(uptime);
    system["load"] = loadText;
    system["processCount"] = processCount;
    system["processCountText"] = QLocale().toString(processCount);
    system["threads"] = QThread::idealThreadCount();
    system["cpuCount"] = m_cpu.value("cores");
    m_system = system;
}

CpuTimes Metrics::parseCpuLine(const QByteArray &line)
{
    CpuTimes times;
    const auto fields = QString::fromUtf8(line).simplified().split(' ', Qt::SkipEmptyParts);
    for (int i = 1; i < fields.size() && i <= 8; ++i)
        times.values[i - 1] = fields.at(i).toLongLong();
    return times;
}

double Metrics::usagePercent(const CpuTimes &before, const CpuTimes &after)
{
    const double total = double(after.total() - before.total());
    const double idle = double(after.idle() - before.idle());
    if (total <= 0)
        return 0;
    return qBound(0.0, (1.0 - idle / total) * 100.0, 100.0);
}

QMap<QString, double> Metrics::parseMeminfo(const QByteArray &text)
{
    QMap<QString, double> values;
    const auto lines = text.split('\n');
    for (const auto &line : lines) {
        const int colon = line.indexOf(':');
        if (colon < 0)
            continue;
        const QString key = QString::fromUtf8(line.left(colon)).trimmed();
        const QString value = QString::fromUtf8(line.mid(colon + 1)).trimmed();
        // Everything in meminfo is in kilobytes.
        values.insert(key, value.section(' ', 0, 0).toDouble() * 1024.0);
    }
    return values;
}

double Metrics::parseClock(const QByteArray &sclk)
{
    // pp_dpm_sclk lists every state, with the active one marked by a star.
    static const QRegularExpression active("^\\d+:\\s*(\\d+)\\s*Mhz", QRegularExpression::CaseInsensitiveOption);
    const auto lines = sclk.split('\n');
    for (const auto &line : lines) {
        if (!line.contains('*'))
            continue;
        const auto match = active.match(QString::fromUtf8(line).trimmed());
        if (match.hasMatch())
            return match.captured(1).toDouble();
    }
    return 0;
}

bool Metrics::parseProcessStat(const QByteArray &stat, ProcessSample &sample)
{
    // The command name is in parentheses and may itself contain spaces or
    // parentheses, so the fields after the last ')' are the only safe split.
    const int open = stat.indexOf('(');
    const int close = stat.lastIndexOf(')');
    if (open < 0 || close < open)
        return false;
    sample.pid = stat.left(open).trimmed().toInt();
    sample.name = QString::fromUtf8(stat.mid(open + 1, close - open - 1));
    const auto fields = QString::fromUtf8(stat.mid(close + 1)).simplified().split(' ', Qt::SkipEmptyParts);
    if (fields.size() < 22)
        return false;
    // fields[0] is state, which is field 3 of the stat line.
    sample.ticks = fields.at(11).toDouble() + fields.at(12).toDouble();
    sample.rss = fields.at(21).toDouble();
    return true;
}

QString Metrics::humanBytes(double bytes)
{
    static const char *units[] = {"B", "KB", "MB", "GB", "TB"};
    int unit = 0;
    double value = qMax(0.0, bytes);
    while (value >= 1024.0 && unit < 4) {
        value /= 1024.0;
        ++unit;
    }
    const int decimals = (unit == 0 || value >= 100) ? 0 : 1;
    return QLocale().toString(value, 'f', decimals) + " " + units[unit];
}

QString Metrics::humanRate(double bytesPerSecond)
{
    return humanBytes(bytesPerSecond) + "/s";
}

QString Metrics::durationText(double seconds)
{
    const qint64 total = qint64(qMax(0.0, seconds));
    const qint64 days = total / 86400;
    const qint64 hours = (total % 86400) / 3600;
    const qint64 minutes = (total % 3600) / 60;
    const QLocale locale;
    if (days > 0)
        return QStringLiteral("%1d %2h").arg(locale.toString(days), locale.toString(hours));
    if (hours > 0)
        return QStringLiteral("%1h %2m").arg(locale.toString(hours), locale.toString(minutes));
    return QStringLiteral("%1m").arg(locale.toString(minutes));
}
