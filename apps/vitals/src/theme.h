#pragma once

#include <QFileSystemWatcher>
#include <QMap>
#include <QObject>
#include <QProcess>
#include <QString>
#include <QTimer>

// Follows the Omarchy theme: the accent used for data, the background and
// foreground the window is built from, and Hyprland's window rounding. A theme
// switch replaces the files, so the watcher re-arms on every change.
class Theme : public QObject {
    Q_OBJECT
    Q_PROPERTY(QString accent READ accent NOTIFY changed)
    Q_PROPERTY(QString accentForeground READ accentForeground NOTIFY changed)
    Q_PROPERTY(QString secondary READ secondary NOTIFY changed)
    Q_PROPERTY(QString background READ background NOTIFY changed)
    Q_PROPERTY(QString panel READ panel NOTIFY changed)
    Q_PROPERTY(QString border READ border NOTIFY changed)
    Q_PROPERTY(QString text READ text NOTIFY changed)
    Q_PROPERTY(QString mutedText READ mutedText NOTIFY changed)
    Q_PROPERTY(bool dark READ dark NOTIFY changed)
    Q_PROPERTY(int radius READ radius NOTIFY changed)

public:
    explicit Theme(const QString &currentDirectory = {}, QObject *parent = nullptr, const QString &hyprctl = {});
    ~Theme() override;

    QString accent() const;
    QString accentForeground() const;
    QString secondary() const;
    QString background() const;
    QString panel() const;
    QString border() const;
    QString text() const;
    QString mutedText() const;
    bool dark() const;
    int radius() const { return m_radius; }

    static QMap<QString, QString> readColors(const QString &path);

signals:
    void changed();

private:
    void reload();
    void refreshRounding();

    QString m_directory;
    QMap<QString, QString> m_colors;
    QFileSystemWatcher m_watcher;
    QTimer m_debounce;
    QString m_hyprctl;
    int m_radius = 0;
    QProcess m_roundingProcess;
    QTimer m_roundingPoll, m_roundingTimeout;
};
