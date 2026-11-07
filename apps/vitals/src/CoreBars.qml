import QtQuick

// One thin bar per core, filled from the bottom, so a busy core stands out at a
// glance without a row of numbers.
Item {
    id: bars

    property var values: []
    property color fill: theme.accent

    Item {
        anchors.fill: parent

        Row {
            anchors.fill: parent
            spacing: 3

            Repeater {
                model: bars.values

                delegate: Item {
                    readonly property int count: bars.values.length
                    width: (bars.width - (count - 1) * 3) / Math.max(1, count)
                    height: bars.height

                    Rectangle {
                        anchors.fill: parent
                        radius: Math.min(2, theme.radius)
                        color: Qt.rgba(theme.text.r, theme.text.g, theme.text.b, 0.08)
                    }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        height: Math.max(1, parent.height * Math.min(1, modelData / 100))
                        radius: Math.min(2, theme.radius)
                        color: bars.fill

                        Behavior on height {
                            NumberAnimation { duration: 220; easing.type: Easing.OutCubic }
                        }
                    }
                }
            }
        }
    }
}
