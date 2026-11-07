import QtQuick
import QtQuick.Layouts

// A card: one section of the reading, with a title that names it and an
// optional subtitle for whatever is worth saying about it right now.
Rectangle {
    id: panel

    property string title: ""
    property string subtitle: ""
    default property alias content: body.data

    color: theme.panel
    border.width: 1
    border.color: theme.border
    radius: theme.radius
    implicitHeight: 220

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            Text {
                text: panel.title
                color: theme.accent
                font.pixelSize: 11
                font.bold: true
                font.letterSpacing: 1.4
                font.capitalization: Font.AllUppercase
            }

            Text {
                Layout.fillWidth: true
                text: panel.subtitle
                color: theme.mutedText
                font.pixelSize: 11
                elide: Text.ElideRight
            }
        }

        Item {
            id: body
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }
}
