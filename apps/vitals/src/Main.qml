import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

ApplicationWindow {
    id: win
    width: 1240
    height: 920
    minimumWidth: 940
    minimumHeight: 720
    visible: true
    title: "vitals"
    color: theme.background

    Material.theme: theme.dark ? Material.Dark : Material.Light
    Material.accent: theme.accent
    Material.roundedScale: theme.radius

    property bool helpVisible: false

    Shortcut { sequence: "?"; context: Qt.ApplicationShortcut; onActivated: win.helpVisible = !win.helpVisible }
    Shortcut { sequence: "Q"; context: Qt.ApplicationShortcut; onActivated: Qt.quit() }
    Shortcut { sequence: "Space"; context: Qt.ApplicationShortcut; onActivated: backend.togglePause() }
    Shortcut { sequence: "R"; context: Qt.ApplicationShortcut; onActivated: backend.refresh() }
    Shortcut { sequence: "I"; context: Qt.ApplicationShortcut; onActivated: backend.cycleInterval() }
    Shortcut { sequence: "Escape"; context: Qt.ApplicationShortcut; onActivated: win.helpVisible = false }

    // Right-to-left languages mirror the window; the Translator sets the
    // application's layout direction.
    Item {
        id: root
        anchors.fill: parent
        LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
        LayoutMirroring.childrenInherit: true

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 18
            spacing: 14

            RowLayout {
                Layout.fillWidth: true
                spacing: 22

                ColumnLayout {
                    spacing: 2

                    Text {
                        text: backend.system.hostname
                        color: theme.text
                        font.pixelSize: 20
                        font.bold: true
                    }

                    Text {
                        Layout.maximumWidth: 520
                        text: backend.system.cpuModel + " · " + backend.system.kernel
                        color: theme.mutedText
                        font.pixelSize: 11
                        elide: Text.ElideRight
                    }
                }

                Item { Layout.fillWidth: true }

                Rectangle {
                    visible: backend.paused
                    implicitWidth: pausedLabel.implicitWidth + 16
                    implicitHeight: pausedLabel.implicitHeight + 6
                    radius: Math.min(4, theme.radius)
                    color: theme.accent

                    Text {
                        id: pausedLabel
                        anchors.centerIn: parent
                        text: qsTr("Paused")
                        color: theme.accentForeground
                        font.pixelSize: 11
                        font.bold: true
                    }
                }

                Chip { label: qsTr("Load"); value: backend.system.load }
                Chip { label: qsTr("Uptime"); value: backend.system.uptimeText }
                Chip { label: qsTr("Processes"); value: backend.system.processCountText }
                Chip { label: qsTr("Every"); value: qsTr("%1 s").arg(backend.interval / 1000) }
            }

            GridLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                columns: 2
                columnSpacing: 14
                rowSpacing: 14

                // CPU
                Panel {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 190
                    title: qsTr("CPU")
                    subtitle: backend.cpu.model

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 16

                            Text {
                                text: backend.cpu.usageText
                                color: theme.text
                                font.pixelSize: 38
                                font.weight: Font.Light
                            }

                            Item { Layout.fillWidth: true }

                            Chip { label: qsTr("Threads"); value: backend.cpu.cores }
                            Chip { label: qsTr("Clock"); value: backend.cpu.clockText }
                            Chip { label: qsTr("Temp"); value: backend.cpu.tempText }
                        }

                        Spark {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumHeight: 34
                            values: backend.cpuHistory
                            maximum: 100
                            stroke: theme.accent
                        }

                        CoreBars {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 32
                            values: backend.cpu.coreUsage
                            fill: theme.accent
                        }
                    }
                }

                // GPU
                Panel {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 190
                    title: qsTr("GPU")
                    subtitle: backend.gpu.present ? backend.gpu.name : qsTr("No GPU found")

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 8
                        visible: backend.gpu.present

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 16

                            Text {
                                text: backend.gpu.usageText
                                color: theme.text
                                font.pixelSize: 38
                                font.weight: Font.Light
                            }

                            Item { Layout.fillWidth: true }

                            Chip { label: qsTr("Temp"); value: backend.gpu.tempText }
                            Chip { label: qsTr("Power"); value: backend.gpu.powerText }
                            Chip { label: qsTr("Fan"); value: backend.gpu.fanText }
                        }

                        Spark {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumHeight: 34
                            values: backend.gpuHistory
                            maximum: 100
                            stroke: theme.accent
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            RowLayout {
                                Layout.fillWidth: true

                                Text {
                                    text: qsTr("VRAM")
                                    color: theme.mutedText
                                    font.pixelSize: 10
                                    font.letterSpacing: 0.8
                                    font.capitalization: Font.AllUppercase
                                }

                                Item { Layout.fillWidth: true }

                                Text {
                                    text: backend.gpu.vramUsedText + " / " + backend.gpu.vramTotalText
                                    color: theme.text
                                    font.pixelSize: 11
                                }
                            }

                            Meter {
                                Layout.fillWidth: true
                                thickness: 5
                                value: backend.gpu.vramUsed
                                maximum: backend.gpu.vramTotal
                                fill: theme.secondary
                            }
                        }
                    }
                }

                // Memory
                Panel {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 170
                    title: qsTr("Memory")
                    subtitle: qsTr("%1 free").arg(backend.memory.freeText)

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 8

                        Text {
                            text: backend.memory.percentText
                            color: theme.text
                            font.pixelSize: 38
                            font.weight: Font.Light
                        }

                        Spark {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumHeight: 34
                            values: backend.memoryHistory
                            maximum: 100
                            stroke: theme.accent
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            RowLayout {
                                Layout.fillWidth: true

                                Text {
                                    text: qsTr("RAM")
                                    color: theme.mutedText
                                    font.pixelSize: 10
                                    font.letterSpacing: 0.8
                                    font.capitalization: Font.AllUppercase
                                }

                                Item { Layout.fillWidth: true }

                                Text {
                                    text: qsTr("%1 of %2").arg(backend.memory.usedText).arg(backend.memory.totalText)
                                    color: theme.text
                                    font.pixelSize: 11
                                }
                            }

                            Meter {
                                Layout.fillWidth: true
                                value: backend.memory.used
                                maximum: backend.memory.total
                                fill: theme.accent
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                Layout.topMargin: 4

                                Text {
                                    text: qsTr("Swap")
                                    color: theme.mutedText
                                    font.pixelSize: 10
                                    font.letterSpacing: 0.8
                                    font.capitalization: Font.AllUppercase
                                }

                                Item { Layout.fillWidth: true }

                                Text {
                                    text: qsTr("%1 of %2").arg(backend.memory.swapUsedText).arg(backend.memory.swapTotalText)
                                    color: theme.text
                                    font.pixelSize: 11
                                }
                            }

                            Meter {
                                Layout.fillWidth: true
                                value: backend.memory.swapUsed
                                maximum: Math.max(1, backend.memory.swapTotal)
                                fill: theme.secondary
                            }
                        }
                    }
                }

                // Disks
                Panel {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 170
                    title: qsTr("Disks")
                    subtitle: qsTr("Read %1 · Write %2").arg(backend.io.readText).arg(backend.io.writeText)
                              + (backend.io.nvmeTempText !== "–" ? " · " + qsTr("NVMe %1").arg(backend.io.nvmeTempText) : "")

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 10

                        ListView {
                            Layout.fillWidth: true
                            Layout.preferredHeight: contentHeight
                            Layout.minimumHeight: 0
                            clip: true
                            spacing: 10
                            model: backend.disks

                            delegate: ColumnLayout {
                                width: ListView.view ? ListView.view.width : 0
                                spacing: 4

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8

                                    Text {
                                        text: modelData.label
                                        color: theme.text
                                        font.pixelSize: 12
                                    }

                                    Text {
                                        text: modelData.type
                                        color: theme.mutedText
                                        font.pixelSize: 10
                                    }

                                    Item { Layout.fillWidth: true }

                                    Text {
                                        text: modelData.usedText + " / " + modelData.totalText
                                        color: theme.mutedText
                                        font.pixelSize: 11
                                    }
                                }

                                Meter {
                                    Layout.fillWidth: true
                                    thickness: 5
                                    value: modelData.used
                                    maximum: modelData.total
                                    fill: theme.accent
                                }
                            }
                        }

                        Item {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 34
                            Layout.minimumHeight: 24

                            Spark {
                                anchors.fill: parent
                                values: backend.ioReadHistory
                                stroke: theme.accent
                            }

                            Spark {
                                anchors.fill: parent
                                values: backend.ioWriteHistory
                                stroke: theme.secondary
                            }
                        }

                        Item { Layout.fillHeight: true }
                    }
                }

                // Network
                Panel {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 190
                    title: qsTr("Network")
                    subtitle: qsTr("%n interface(s)", "", backend.networks.length)

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 20

                            Text {
                                text: "↓ " + backend.network.inText
                                color: theme.accent
                                font.pixelSize: 20
                            }

                            Text {
                                text: "↑ " + backend.network.outText
                                color: theme.secondary
                                font.pixelSize: 20
                            }

                            Item { Layout.fillWidth: true }
                        }

                        Item {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumHeight: 34

                            Spark {
                                anchors.fill: parent
                                values: backend.networkInHistory
                                stroke: theme.accent
                            }

                            Spark {
                                anchors.fill: parent
                                values: backend.networkOutHistory
                                stroke: theme.secondary
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2

                            Repeater {
                                model: backend.networks

                                delegate: RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8

                                    Text {
                                        text: modelData.name
                                        color: theme.text
                                        font.pixelSize: 11
                                    }

                                    Item { Layout.fillWidth: true }

                                    Text {
                                        text: "↓ " + modelData.inText
                                        color: theme.mutedText
                                        font.pixelSize: 11
                                    }

                                    Text {
                                        text: "↑ " + modelData.outText
                                        color: theme.mutedText
                                        font.pixelSize: 11
                                    }
                                }
                            }
                        }
                    }
                }

                // Processes
                Panel {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 190
                    title: qsTr("Processes")
                    subtitle: qsTr("Busiest first")

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 5

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12

                            Text {
                                Layout.fillWidth: true
                                text: qsTr("Name")
                                color: theme.mutedText
                                font.pixelSize: 10
                                font.letterSpacing: 0.8
                                font.capitalization: Font.AllUppercase
                            }

                            Text {
                                Layout.preferredWidth: 58
                                text: qsTr("CPU")
                                horizontalAlignment: Text.AlignRight
                                color: theme.mutedText
                                font.pixelSize: 10
                                font.letterSpacing: 0.8
                                font.capitalization: Font.AllUppercase
                            }

                            Text {
                                Layout.preferredWidth: 76
                                text: qsTr("Memory")
                                horizontalAlignment: Text.AlignRight
                                color: theme.mutedText
                                font.pixelSize: 10
                                font.letterSpacing: 0.8
                                font.capitalization: Font.AllUppercase
                            }
                        }

                        ListView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            spacing: 5
                            model: backend.processes

                            delegate: RowLayout {
                                width: ListView.view ? ListView.view.width : 0
                                spacing: 12

                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.name
                                    color: theme.text
                                    font.pixelSize: 12
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.preferredWidth: 58
                                    text: modelData.cpuText
                                    horizontalAlignment: Text.AlignRight
                                    color: theme.text
                                    font.pixelSize: 12
                                }

                                Text {
                                    Layout.preferredWidth: 76
                                    text: modelData.memoryText
                                    horizontalAlignment: Text.AlignRight
                                    color: theme.mutedText
                                    font.pixelSize: 12
                                }
                            }
                        }
                    }
                }
            }
        }

        // Shortcuts, over everything, dismissed by ? or Escape.
        Rectangle {
            anchors.fill: parent
            visible: win.helpVisible
            color: Qt.rgba(0, 0, 0, 0.72)

            MouseArea {
                anchors.fill: parent
                onClicked: win.helpVisible = false
            }

            Rectangle {
                anchors.centerIn: parent
                width: Math.min(420, parent.width - 60)
                height: helpColumn.implicitHeight + 40
                color: theme.panel
                border.width: 1
                border.color: theme.border
                radius: theme.radius

                ColumnLayout {
                    id: helpColumn
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 9

                    Text {
                        text: qsTr("Shortcuts")
                        color: theme.accent
                        font.pixelSize: 11
                        font.bold: true
                        font.letterSpacing: 1.4
                        font.capitalization: Font.AllUppercase
                    }

                    Repeater {
                        model: [
                            { "key": "Space", "action": qsTr("Pause or resume sampling") },
                            { "key": "R", "action": qsTr("Refresh now") },
                            { "key": "I", "action": qsTr("Change the interval") },
                            { "key": "?", "action": qsTr("Show these shortcuts") },
                            { "key": "Q", "action": qsTr("Quit") }
                        ]

                        delegate: RowLayout {
                            Layout.fillWidth: true
                            spacing: 16

                            Text {
                                Layout.preferredWidth: 64
                                text: modelData.key
                                color: theme.text
                                font.pixelSize: 12
                                font.bold: true
                            }

                            Text {
                                Layout.fillWidth: true
                                text: modelData.action
                                color: theme.text
                                font.pixelSize: 12
                            }
                        }
                    }
                }
            }
        }
    }
}
