import QtQuick

// A filled bar: a translucent track with the value drawn over it. The width is
// animated so a change reads as movement rather than a jump.
Item {
    id: meter

    property real value: 0
    property real maximum: 1
    property color fill: theme.accent
    property int thickness: 6

    implicitHeight: thickness
    implicitWidth: 100

    Rectangle {
        anchors.fill: parent
        radius: Math.min(3, theme.radius)
        color: Qt.rgba(theme.text.r, theme.text.g, theme.text.b, 0.10)
    }

    Rectangle {
        height: parent.height
        radius: Math.min(3, theme.radius)
        color: meter.fill
        width: Math.max(0, Math.min(1, meter.maximum > 0 ? meter.value / meter.maximum : 0)) * parent.width

        Behavior on width {
            NumberAnimation { duration: 220; easing.type: Easing.OutCubic }
        }
    }
}
