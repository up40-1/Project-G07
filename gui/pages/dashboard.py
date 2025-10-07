import os
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QFrame, QGridLayout)
from PyQt6.QtCore import Qt, QTimer, QMargins, QEasingCurve, QRect, pyqtProperty, pyqtSignal, QSize, QAbstractAnimation, QByteArray
from PyQt6.QtCore import QPropertyAnimation
from PyQt6.QtCharts import QChart, QChartView, QDateTimeAxis, QValueAxis, QLineSeries
from PyQt6.QtCharts import QSplineSeries
from PyQt6.QtGui import QPainter, QColor, QPen, QPixmap
import math, platform, subprocess, shutil, time

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover
    psutil = None
try:
    import GPUtil  # type: ignore  # For NVIDIA fallback
except Exception:  # pragma: no cover
    GPUtil = None
try:
    from pynvml import (  # type: ignore
        nvmlInit, nvmlShutdown, nvmlDeviceGetCount, nvmlDeviceGetHandleByIndex,
        nvmlDeviceGetUtilizationRates, NVMLError
    )
except Exception:  # pragma: no cover
    nvmlInit = nvmlShutdown = nvmlDeviceGetCount = nvmlDeviceGetHandleByIndex = nvmlDeviceGetUtilizationRates = None
    NVMLError = Exception


class GPUUsageProvider:
    def __init__(self, sample_interval: float = 3.0):
        self.last_sample_time = 0.0
        self.cached = None
        self.sample_interval = sample_interval
        self._nvml_inited = False
        self._is_windows = platform.system().lower().startswith('win')

    def _init_nvml(self):
        if nvmlInit and not self._nvml_inited:
            try:
                nvmlInit()
                self._nvml_inited = True
            except Exception:
                self._nvml_inited = False

    def _sample_nvml(self):
        if not nvmlInit:
            return None
        try:
            self._init_nvml()
            if not self._nvml_inited:
                return None
            count = nvmlDeviceGetCount()
            if count < 1:
                return None
            handle = nvmlDeviceGetHandleByIndex(0)
            util = nvmlDeviceGetUtilizationRates(handle)
            return float(util.gpu)
        except NVMLError:
            return None
        except Exception:
            return None

    def _sample_gputil(self):
        if not GPUtil:
            return None
        try:
            g_list = GPUtil.getGPUs()
            if not g_list:
                return None
            return g_list[0].load * 100.0
        except Exception:
            return None

    def _sample_rocm(self):
        if platform.system().lower() != 'linux':
            return None
        if not shutil.which('rocm-smi'):
            return None
        try:
            proc = subprocess.run(['rocm-smi', '--showuse'], capture_output=True, text=True, timeout=1.5)
            out = proc.stdout
            for line in out.splitlines():
                if '%' in line:
                    parts = line.replace('%',' ').split()
                    for p in parts:
                        if p.isdigit():
                            val = int(p)
                            if 0 <= val <= 100:
                                return float(val)
        except Exception:
            return None
        return None

    def _sample_windows_counter(self):
        if not self._is_windows:
            return None
        ps = shutil.which('powershell') or shutil.which('pwsh')
        if not ps:
            return None
        try:
            cmd = [ps, '-NoLogo', '-NoProfile', '-Command', 'Get-Counter -Counter "\\GPU Engine(*)\\Utilization Percentage" -ErrorAction SilentlyContinue | Select -ExpandProperty CounterSamples | Select -ExpandProperty CookedValue']
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1.8)
            if proc.returncode != 0:
                return None
            values = []
            for line in proc.stdout.strip().splitlines():
                try:
                    v = float(line.strip())
                    if 0 <= v <= 1000:
                        values.append(v)
                except Exception:
                    pass
            if not values:
                return None
            avg = sum(values)/len(values)
            return max(0.0, min(100.0, avg))
        except Exception:
            return None

    def sample(self):
        now = time.time()
        if now - self.last_sample_time < self.sample_interval and self.cached is not None:
            return self.cached
        methods = [self._sample_nvml, self._sample_gputil, self._sample_rocm, self._sample_windows_counter]
        for m in methods:
            val = m()
            if val is not None:
                self.cached = val
                self.last_sample_time = now
                return val
        self.cached = None
        self.last_sample_time = now
        return None
from gui.styles import Styles
from utils.config_manager import ConfigManager

class NoScrollChartView(QChartView):
    def wheelEvent(self, event):
        event.ignore()


class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.init_ui()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(5000)
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        self.series_animating = False
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        welcome_frame = QFrame()
        welcome_frame.setStyleSheet(Styles.CARD)
        wf_outer = QHBoxLayout(welcome_frame)
        wf_outer.setContentsMargins(8, 8, 8, 8)
        wf_outer.setSpacing(24)

        left_box = QVBoxLayout()
        left_box.setSpacing(6)
        pc_name = os.environ.get('COMPUTERNAME', 'User')
        welcome_label = QLabel(f"Welcome back, {pc_name}!")
        welcome_label.setStyleSheet(Styles.LABEL_TITLE)
        left_box.addWidget(welcome_label)
        subtitle = QLabel("Here's what's happening with your clients today")
        subtitle.setStyleSheet(Styles.LABEL_SUBTITLE)
        left_box.addWidget(subtitle)
        left_box.addStretch()
        wf_outer.addLayout(left_box, 1)

        dials_frame = QFrame()
        dials_layout = QHBoxLayout(dials_frame)
        dials_layout.setContentsMargins(0, 0, 0, 0)
        dials_layout.setSpacing(26)

        self.cpu_dial = UsageDial(label="CPU", color="#4caf50")
        self.ram_dial = UsageDial(label="RAM", color="#ffa726")
        for dial in (self.cpu_dial, self.ram_dial):
            dials_layout.addWidget(dial)

        wf_outer.addWidget(dials_frame, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(welcome_frame)

        self.res_timer = QTimer(self)
        self.res_timer.timeout.connect(self.update_resource_dials)
        self.res_timer.start(1000)

        circles_layout = QGridLayout()
        circles_layout.setSpacing(24)

        total_card, self.total_circle = self.create_circular_stat("Total", Styles.TEXT)
        online_card, self.online_circle = self.create_circular_stat("Online", Styles.SUCCESS)
        offline_card, self.offline_circle = self.create_circular_stat("Offline", Styles.ERROR)
        today_card, self.today_circle = self.create_circular_stat("Today", Styles.WARNING)

        circles_layout.addWidget(total_card, 0, 0)
        circles_layout.addWidget(online_card, 0, 1)
        circles_layout.addWidget(offline_card, 0, 2)
        circles_layout.addWidget(today_card, 0, 3)

        layout.addLayout(circles_layout)

        chart_frame = QFrame()
        chart_frame.setStyleSheet(Styles.CARD)
        chart_layout = QVBoxLayout(chart_frame)

        chart_title = QLabel("30-Day Client Activity")
        chart_title.setStyleSheet(f"color: {Styles.TEXT}; font-size: 20px; font-weight: bold; padding-top: 6px;")
        chart_layout.setContentsMargins(8, 10, 8, 8)
        chart_layout.addWidget(chart_title)

        self.chart_view = self.create_chart()
        self.chart_view.setMinimumHeight(280)
        self.chart_view.setMaximumHeight(360)
        chart_layout.addWidget(self.chart_view)
        self.chart_tooltip = QLabel("", self.chart_view)
        self.chart_tooltip.setStyleSheet("background-color: rgba(0,0,0,160); color: #ffffff; padding:4px 8px; border-radius:6px; font-size:12px;")
        self.chart_tooltip.hide()
        self.chart_view.setMouseTracking(True)
        self.chart_view.viewport().installEventFilter(self)

        layout.addWidget(chart_frame, 1)

        self.update_stats()
        self.update_resource_dials()

    def update_resource_dials(self):
        cpu = None
        if psutil:
            try:
                cpu = psutil.cpu_percent(interval=None)
            except Exception:
                cpu = None
        if cpu is not None:
            self.cpu_dial.set_target(cpu)
        else:
            self.cpu_dial.set_unavailable()

        ram = None
        if psutil:
            try:
                ram = psutil.virtual_memory().percent
            except Exception:
                ram = None
        if ram is not None:
            self.ram_dial.set_target(ram)
        else:
            self.ram_dial.set_unavailable()
    
    def create_circular_stat(self, title, color):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {Styles.CARD_BG};
                border-radius: 18px;
                padding: 12px 12px 16px 12px;
            }}
        """)
        v = QVBoxLayout(card)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(8)
        title_lbl = QLabel(title)
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        title_lbl.setStyleSheet(f"color: {Styles.TEXT_SECONDARY}; font-size:13px; letter-spacing:1px;")
        v.addWidget(title_lbl)
        circle = CircularCounter(color=color)
        circle.setFixedSize(130, 130)
        v.addWidget(circle, 1, Qt.AlignmentFlag.AlignHCenter)
        return card, circle
    
    def create_chart(self):
        """Create 30-day chart using smooth spline (wave) line with progressive animation."""
        series = QSplineSeries()
        series.setName("New Clients")
        try:
            series.setUseOpenGL(True)
        except Exception:
            pass

        client_history = self.config.get('client_history', {})
        today = datetime.now()
        max_count = 0
        for i in range(30, -1, -1):
            date = today - timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            count = client_history.get(date_str, 0)
            series.append(date.timestamp() * 1000, count)
            if count > max_count:
                max_count = count

        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("")
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart.setBackgroundBrush(QColor("#161616"))
        chart.setTitleBrush(QColor("#f5f5f5"))
        chart.legend().setVisible(False)

        axis_x = QDateTimeAxis()
        axis_x.setFormat("MMM dd")
        axis_x.setLabelsColor(QColor("#9d9d9d"))
        axis_x.setGridLineColor(QColor("#222222"))
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setLabelFormat("%d")
        axis_y.setLabelsColor(QColor("#9d9d9d"))
        axis_y.setGridLineColor(QColor("#222222"))
        upper = max_count if max_count > 0 else 1
        axis_y.setRange(0, upper + max(1, upper * 0.15))
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)

        pen = QPen(QColor("#f5f5f5"))
        pen.setWidth(3)
        pen.setCosmetic(True)
        series.setPen(pen)
        series.setPointsVisible(False)

        chart.setMargins(QMargins(16, 18, 60, 46))

        chart_view = NoScrollChartView(chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        chart_view.setRubberBand(QChartView.RubberBand.NoRubberBand)
        try:
            from PyQt6.QtCore import Qt as _Qt
            chart_view.setHorizontalScrollBarPolicy(_Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            chart_view.setVerticalScrollBarPolicy(_Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        except Exception:
            pass
        chart_view.setStyleSheet("background: transparent; border: none;")

        def _start_reveal():
            vp = chart_view.viewport()
            w = vp.width()
            h = vp.height()
            overlay = QWidget(vp)
            overlay.setStyleSheet(f"background-color: {Styles.CARD_BG}; border: none;")
            overlay.setGeometry(0, 0, w, h)
            overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            overlay.show()

            anim = QPropertyAnimation(overlay, b"geometry")
            anim.setDuration(1800)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.setStartValue(QRect(0, 0, w, h))
            anim.setEndValue(QRect(w, 0, 0, h))
            anim.start()
            self._reveal_anim = anim
            self._chart_overlay = overlay

        QTimer.singleShot(0, _start_reveal)

        return chart_view

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent, QPointF
        if obj is self.chart_view.viewport():
            if getattr(self, 'series_animating', False):
                self.chart_tooltip.hide()
                return False
            if event.type() == event.Type.MouseMove:
                pos = event.position()
                chart = self.chart_view.chart()
                series_list = chart.series()
                if not series_list:
                    return False
                series = series_list[0]
                vp_rect = self.chart_view.viewport().rect()
                if not vp_rect.contains(pos.toPoint()):
                    self.chart_tooltip.hide()
                    return False
                chart_pos = self.chart_view.mapToScene(pos.toPoint())
                if series.count() < 2:
                    self.chart_tooltip.hide()
                    return super().eventFilter(obj, event)
                points = [series.at(i) for i in range(series.count())]
                try:
                    first_scene = chart.mapToPosition(points[0], series)
                    last_scene = chart.mapToPosition(points[-1], series)
                    first_vp = self.chart_view.mapFromScene(first_scene)
                    last_vp = self.chart_view.mapFromScene(last_scene)
                    mouse_vp = pos.toPoint()
                    span = last_vp.x() - first_vp.x()
                    if span == 0:
                        frac = 0.0
                    else:
                        frac = (mouse_vp.x() - first_vp.x()) / float(span)
                    if frac < 0.0: frac = 0.0
                    if frac > 1.0: frac = 1.0
                    min_x = points[0].x(); max_x = points[-1].x()
                    px = min_x + frac * (max_x - min_x)
                except Exception:
                    plot_rect = chart.plotArea()
                    chart_pos_chart = chart.mapFromScene(chart_pos)
                    cx_chart = chart_pos_chart.x()
                    if cx_chart < plot_rect.left():
                        cx_chart = plot_rect.left()
                    if cx_chart > plot_rect.right():
                        cx_chart = plot_rect.right()
                    frac = 0.0 if plot_rect.width() == 0 else (cx_chart - plot_rect.left()) / float(plot_rect.width())
                    min_x = points[0].x(); max_x = points[-1].x()
                    px = min_x + frac * (max_x - min_x)

                left = points[0]; right = points[-1]
                for i in range(1, len(points)):
                    if points[i].x() >= px:
                        left = points[i-1]
                        right = points[i]
                        break
                if right.x() == left.x():
                    y_val = left.y(); ratio = 0.0
                else:
                    ratio = (px - left.x()) / (right.x() - left.x())
                    y_val = left.y() + (right.y() - left.y()) * ratio
                tooltip_text = f"{int(round(y_val))} clients"
                self.chart_tooltip.setText(tooltip_text)
                self.chart_tooltip.adjustSize()
                tx = int(event.position().x() - self.chart_tooltip.width()/2)
                ty = int(event.position().y() - 40)
                if tx < 4: tx = 4
                max_x = self.chart_view.width() - self.chart_tooltip.width() - 4
                if tx > max_x: tx = max_x
                if ty < 8: ty = 8
                max_y = self.chart_view.height() - self.chart_tooltip.height() - 8
                if ty > max_y: ty = max_y
                self.chart_tooltip.move(tx, ty)
                self.chart_tooltip.show()

                if not hasattr(self, '_hover_line') or self._hover_line is None:
                    from PyQt6.QtWidgets import QFrame
                    line = QFrame(self.chart_view.viewport())
                    line.setStyleSheet("background-color: #ffffff22; border: 1px solid #ffffff55; border-radius:1px;")
                    line.setFrameShape(QFrame.Shape.NoFrame)
                    self._hover_line = line
                line = self._hover_line
                scene_left = chart.mapToScene(chart.mapToPosition(left, series))
                scene_right = chart.mapToScene(chart.mapToPosition(right, series))
                if right.x() == left.x():
                    line_scene_x = scene_left.x()
                else:
                    line_scene_x = scene_left.x() + (scene_right.x() - scene_left.x()) * ratio
                plot_rect = chart.plotArea()
                scene_top = chart.mapToScene(line_scene_x, plot_rect.top())
                scene_bottom = chart.mapToScene(line_scene_x, plot_rect.bottom())
                top_left_scene = chart.mapToScene(plot_rect.topLeft())
                bottom_right_scene = chart.mapToScene(plot_rect.bottomRight())
                top_left_vp = self.chart_view.mapFromScene(top_left_scene)
                bottom_right_vp = self.chart_view.mapFromScene(bottom_right_scene)
                line_x_vp = self.chart_view.mapFromScene(scene_top).x()
                line.setGeometry(int(line_x_vp)-1, int(top_left_vp.y()), 2, int(bottom_right_vp.y() - top_left_vp.y()))
                line.show()
            elif event.type() == event.Type.Leave:
                self.chart_tooltip.hide()
                if hasattr(self, '_hover_line') and self._hover_line:
                    self._hover_line.hide()
        return super().eventFilter(obj, event)
    
    def update_stats(self):
        try:
            self.config.load()
        except Exception:
            pass

        clients = self.config.get('clients', [])
        
        total = len(clients)
        online = sum(1 for c in clients if c.get('status') == 'online')
        offline = total - online
        
        today = datetime.now().strftime('%Y-%m-%d')
        today_count = 0
        for client in clients:
            if client.get('first_seen', '').startswith(today):
                today_count += 1
        max_base = total if total > 0 else 1
        try:
            self.total_circle.animate_to(total if total > 0 else 0, max_value=max_base)
        except Exception:
            pass
        try:
            self.online_circle.animate_to(online, max_value=max_base)
        except Exception:
            pass
        try:
            self.offline_circle.animate_to(offline, max_value=max_base)
        except Exception:
            pass
        try:
            self.today_circle.animate_to(today_count, max_value=max_base)
        except Exception:
            pass


class CircularCounter(QWidget):
    valueChanged = pyqtSignal()

    def __init__(self, color="#ffffff", parent=None):
        super().__init__(parent)
        self._value = 0
        self._target = 0
        self._max = 1
        self._color = color
        self._anim = None
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.valueChanged.connect(self.update)

    def sizeHint(self):
        return self.minimumSizeHint()

    def minimumSizeHint(self):
        return QSize(120, 120)

    @pyqtProperty(int)
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        if self._value != v:
            self._value = v
            self.valueChanged.emit()

    def animate_to(self, target, max_value=None):
        if max_value is not None:
            self._max = max_value if max_value > 0 else 1
        self._target = target
        if self._anim and self._anim.state() == QAbstractAnimation.Running:
            self._anim.stop()
        self.value = 0
        self._anim = QPropertyAnimation(self, b"value")
        self._anim.setStartValue(0)
        self._anim.setEndValue(target)
        base = 900
        extra = min(1100, target * 25)
        self._anim.setDuration(base + extra)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._anim.start()

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QPen, QFont
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(6, 6, -6, -6)
        diameter = min(rect.width(), rect.height())
        square = QRect(rect.center().x() - diameter//2, rect.center().y() - diameter//2, diameter, diameter)

        bg_pen = QPen(QColor(80, 80, 80, 90), 10)
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen)
        painter.drawArc(square, 0, 360 * 16)

        progress = 0 if self._max == 0 else min(1.0, float(self._value)/float(self._max))
        span = int(progress * 360 * 16)
        fg_pen = QPen(QColor(self._color), 10)
        fg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(fg_pen)
        painter.drawArc(square, 90 * 16, -span)

        painter.setPen(QColor(self._color))
        font = QFont()
        font.setPointSize(20)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(square, Qt.AlignmentFlag.AlignCenter, str(self._value))


class UsageDial(QWidget):
    def __init__(self, label: str, color: str = "#4caf50", parent=None):
        super().__init__(parent)
        self._label = label
        self._color = color
        self._value = 0.0
        self._target = 0.0
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._step_animation)
        self._anim_timer.start(40)
        self._unavailable = False
        self.setFixedSize(90, 90)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def set_target(self, pct: float):
        if pct is None or pct < 0:
            self.set_unavailable()
            return
        self._unavailable = False
        self._target = max(0.0, min(100.0, float(pct)))

    def set_unavailable(self):
        self._unavailable = True
        self._target = 0.0

    def _step_animation(self):
        diff = self._target - self._value
        if abs(diff) < 0.1:
            self._value = self._target
        else:
            self._value += diff * 0.15
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(6, 6, -6, -6)
        diameter = min(rect.width(), rect.height())
        box = QRect(rect.center().x() - diameter//2, rect.center().y() - diameter//2, diameter, diameter)

        bg_pen = QPen(QColor(90, 90, 90, 110), 8)
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen)
        painter.drawArc(box, 0, 360 * 16)

        pen = QPen(QColor(self._color), 8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        span = int((self._value / 100.0) * 360 * 16)
        painter.drawArc(box, 90 * 16, -span)

        painter.setPen(QColor(self._color if not self._unavailable else '#666666'))
        font = painter.font()
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)
        if self._unavailable:
            txt = f"{self._label}\nN/A"
        else:
            txt = f"{self._label}\n{int(round(self._value))}%"
        painter.drawText(box, Qt.AlignmentFlag.AlignCenter, txt)
