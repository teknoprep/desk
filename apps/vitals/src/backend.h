#pragma once

#include <QObject>
#include <QTimer>

#include "metrics.h"

// Ticks the sampler and hands the reading to QML. QML only reads these
// properties; pausing stops the timer but still allows a manual refresh, and a
// pause keeps the last reading on screen rather than blanking the window.
class Backend : public QObject {
    Q_OBJECT
    Q_PROPERTY(QVariantMap cpu READ cpu NOTIFY sampled)
    Q_PROPERTY(QVariantMap gpu READ gpu NOTIFY sampled)
    Q_PROPERTY(QVariantMap memory READ memory NOTIFY sampled)
    Q_PROPERTY(QVariantMap system READ system NOTIFY sampled)
    Q_PROPERTY(QVariantMap io READ io NOTIFY sampled)
    Q_PROPERTY(QVariantMap network READ network NOTIFY sampled)
    Q_PROPERTY(QVariantList disks READ disks NOTIFY sampled)
    Q_PROPERTY(QVariantList networks READ networks NOTIFY sampled)
    Q_PROPERTY(QVariantList processes READ processes NOTIFY sampled)
    Q_PROPERTY(QVariantList cpuHistory READ cpuHistory NOTIFY sampled)
    Q_PROPERTY(QVariantList gpuHistory READ gpuHistory NOTIFY sampled)
    Q_PROPERTY(QVariantList networkInHistory READ networkInHistory NOTIFY sampled)
    Q_PROPERTY(QVariantList networkOutHistory READ networkOutHistory NOTIFY sampled)
    Q_PROPERTY(QVariantList memoryHistory READ memoryHistory NOTIFY sampled)
    Q_PROPERTY(QVariantList ioReadHistory READ ioReadHistory NOTIFY sampled)
    Q_PROPERTY(QVariantList ioWriteHistory READ ioWriteHistory NOTIFY sampled)
    Q_PROPERTY(bool paused READ paused NOTIFY pausedChanged)
    Q_PROPERTY(int interval READ interval NOTIFY intervalChanged)

public:
    explicit Backend(QObject *parent = nullptr);

    QVariantMap cpu() const { return m_metrics.cpu(); }
    QVariantMap gpu() const { return m_metrics.gpu(); }
    QVariantMap memory() const { return m_metrics.memory(); }
    QVariantMap system() const { return m_metrics.system(); }
    QVariantMap io() const { return m_metrics.io(); }
    QVariantMap network() const { return m_metrics.network(); }
    QVariantList disks() const { return m_metrics.disks(); }
    QVariantList networks() const { return m_metrics.networks(); }
    QVariantList processes() const { return m_metrics.processes(); }
    QVariantList cpuHistory() const { return m_metrics.cpuHistory(); }
    QVariantList gpuHistory() const { return m_metrics.gpuHistory(); }
    QVariantList networkInHistory() const { return m_metrics.networkInHistory(); }
    QVariantList networkOutHistory() const { return m_metrics.networkOutHistory(); }
    QVariantList memoryHistory() const { return m_metrics.memoryHistory(); }
    QVariantList ioReadHistory() const { return m_metrics.ioReadHistory(); }
    QVariantList ioWriteHistory() const { return m_metrics.ioWriteHistory(); }

    bool paused() const { return m_paused; }
    int interval() const { return m_interval; }

    Q_INVOKABLE void refresh();
    Q_INVOKABLE void togglePause();
    // 1 s -> 2 s -> 5 s -> 1 s, so the window can be left open without
    // sampling every second forever.
    Q_INVOKABLE void cycleInterval();

signals:
    void sampled();
    void pausedChanged();
    void intervalChanged();

private:
    void setInterval(int milliseconds);

    Metrics m_metrics;
    QTimer m_timer;
    int m_interval = 1000;
    bool m_paused = false;
};
