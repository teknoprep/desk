import QtQuick
import QtQuick.Layouts

// A small label above a value, for the handful of numbers that do not deserve
// a whole meter.
ColumnLayout {
    id: chip

    property string label: ""
    property string value: ""
    property color valueColor: theme.text

    spacing: 1

    Text {
        text: chip.label
        color: theme.mutedText
        font.pixelSize: 10
        font.letterSpacing: 0.8
        font.capitalization: Font.AllUppercase
    }

    Text {
        text: chip.value
        color: chip.valueColor
        font.pixelSize: 13
    }
}
