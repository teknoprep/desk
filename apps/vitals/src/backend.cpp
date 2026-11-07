#include "backend.h"

#include <QTimer>

Backend::Backend(QObject *parent)
    : QObject(parent)
{
    // A first reading only sets the baselines the deltas are measured against,
    // so take a second one shortly after to fill the window straight away.
    m_metrics.sample();
    QTimer::singleShot(300, this, &Backend::refresh);

    m_timer.setInterval(m_interval);
    connect(&m_timer, &QTimer::timeout, this, &Backend::refresh);
    m_timer.start();
}

void Backend::refresh()
{
    m_metrics.sample();
    emit sampled();
}

void Backend::togglePause()
{
    m_paused = !m_paused;
    if (m_paused) {
        // Pausing leaves the last reading on screen untouched.
        m_timer.stop();
    } else {
        // The counters kept running while the window was paused, so measure
        // from a fresh baseline rather than averaging the pause into a rate.
        m_metrics.resetBaselines();
        m_timer.start();
    }
    emit pausedChanged();
}

void Backend::cycleInterval()
{
    static const int intervals[] = {1000, 2000, 5000};
    int index = 0;
    for (int i = 0; i < 3; ++i)
        if (intervals[i] == m_interval)
            index = i;
    setInterval(intervals[(index + 1) % 3]);
}

void Backend::setInterval(int milliseconds)
{
    if (milliseconds == m_interval)
        return;
    m_interval = milliseconds;
    m_timer.setInterval(milliseconds);
    emit intervalChanged();
}
