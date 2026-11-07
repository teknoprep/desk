#pragma once

#include <QHash>
#include <QList>
#include <QMap>
#include <QString>
#include <QVariantList>
#include <QVariantMap>

// The eight busy/idle counters of a /proc/stat line.
struct CpuTimes {
    qint64 values[8] = {0, 0, 0, 0, 0, 0, 0, 0};  // user nice system idle iowait irq softirq steal
    qint64 total() const;
    qint64 idle() const;
};

struct ProcessSample {
    int pid = 0;
    QString name;
    double ticks = 0;  // utime + stime, in clock ticks
    double rss = 0;    // resident pages
};

// One reading of the machine, taken from procfs and sysfs: nothing external is
// run, and no privilege is needed. Backend owns the timer; everything here is
// plain data. The parsers are static so the tests can feed them synthetic text
// instead of whatever the running machine happens to be doing.
class Metrics {
public:
    Metrics();

    void sample();
    // Forget the counters the deltas are measured against, so the next sample
    // starts a fresh baseline instead of averaging over a pause.
    void resetBaselines();

    QVariantMap cpu() const { return m_cpu; }
    QVariantMap gpu() const { return m_gpu; }
    QVariantMap memory() const { return m_memory; }
    QVariantMap system() const { return m_system; }
    QVariantMap io() const { return m_io; }
    QVariantMap network() const { return m_network; }
    QVariantList disks() const { return m_disks; }
    QVariantList networks() const { return m_networks; }
    QVariantList processes() const { return m_processes; }
    QVariantList cpuHistory() const { return m_cpuHistory; }
    QVariantList gpuHistory() const { return m_gpuHistory; }
    QVariantList networkInHistory() const { return m_networkIn; }
    QVariantList networkOutHistory() const { return m_networkOut; }
    QVariantList memoryHistory() const { return m_memoryHistory; }
    QVariantList ioReadHistory() const { return m_ioReadHistory; }
    QVariantList ioWriteHistory() const { return m_ioWriteHistory; }

    static CpuTimes parseCpuLine(const QByteArray &line);
    static double usagePercent(const CpuTimes &before, const CpuTimes &after);
    static QMap<QString, double> parseMeminfo(const QByteArray &text);
    static double parseClock(const QByteArray &sclk);
    static bool parseProcessStat(const QByteArray &stat, ProcessSample &sample);
    static QString humanBytes(double bytes);
    static QString humanRate(double bytesPerSecond);
    static QString durationText(double seconds);

private:
    void findGpu();
    void sampleCpu();
    void sampleMemory();
    void sampleGpu();
    void sampleDisks(double seconds);
    void sampleNetwork(double seconds);
    void sampleProcesses(double seconds);
    void sampleSystem();
    void push(QVariantList &history, double value);

    QString m_gpuDevice;
    QString m_gpuHwmon;
    QString m_gpuName;
    QString m_cpuModel;
    qint64 m_lastSample = 0;

    CpuTimes m_previousTotal;
    QList<CpuTimes> m_previousCores;
    bool m_hasCpu = false;
    QHash<QString, QPair<quint64, quint64>> m_previousNetwork;
    QHash<int, double> m_previousProcessTicks;
    quint64 m_previousRead = 0;
    quint64 m_previousWritten = 0;
    bool m_hasIo = false;

    double m_cpuUsage = 0;
    double m_gpuUsage = 0;
    double m_netInRate = 0;
    double m_netOutRate = 0;
    double m_memoryPercent = 0;
    double m_ioReadRate = 0;
    double m_ioWriteRate = 0;

    QVariantMap m_cpu, m_gpu, m_memory, m_system, m_io, m_network;
    QVariantList m_disks, m_networks, m_processes;
    QVariantList m_cpuHistory, m_gpuHistory, m_networkIn, m_networkOut;
    QVariantList m_memoryHistory, m_ioReadHistory, m_ioWriteHistory;
};
