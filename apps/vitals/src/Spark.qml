import QtQuick

// A line chart of the last ninety readings, with the area under it filled in.
// Percentages get a fixed 100, so their height means something; rates scale to
// the largest value in the window instead.
Canvas {
    id: spark

    property var values: []
    property real maximum: 0
    property color stroke: theme.accent

    onValuesChanged: requestPaint()
    onMaximumChanged: requestPaint()
    onStrokeChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()

    onPaint: {
        var ctx = getContext("2d");
        var w = width;
        var h = height;
        ctx.clearRect(0, 0, w, h);
        if (values.length < 2 || w <= 0 || h <= 0)
            return;

        var top = maximum;
        if (top <= 0) {
            var peak = 0;
            for (var i = 0; i < values.length; ++i)
                peak = Math.max(peak, values[i]);
            top = Math.max(peak * 1.15, 1);
        }

        var x, y;
        ctx.beginPath();
        ctx.moveTo(0, h - Math.min(1, values[0] / top) * h);
        for (var j = 1; j < values.length; ++j) {
            x = j / (values.length - 1) * w;
            y = h - Math.min(1, values[j] / top) * h;
            ctx.lineTo(x, y);
        }
        ctx.lineWidth = 1.5;
        ctx.strokeStyle = stroke;
        ctx.stroke();

        ctx.lineTo(w, h);
        ctx.lineTo(0, h);
        ctx.closePath();
        ctx.fillStyle = Qt.rgba(stroke.r, stroke.g, stroke.b, 0.18);
        ctx.fill();
    }
}
