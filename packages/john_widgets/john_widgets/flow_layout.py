from __future__ import annotations

from typing import List, Optional, Tuple

from PyQt6.QtCore import Qt, QPoint, QRect, QSize, QEvent
from PyQt6.QtWidgets import (
    QWidget,
    QLayout,
    QLayoutItem,
    QSizePolicy,
)
from PyQt6.QtGui import QPainter, QPen, QColor, QPaintEvent


class FlowLayout(QLayout):
    """
    A standard QLayout that arranges child widgets from left to right, 
    wrapping to new lines. 
    It calculates the exact height required for the given width.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._item_list: List[QLayoutItem] = []
        self._line_debug_positions: List[Tuple[int, int]] = []

        # Configuration
        self.grid_enabled: bool = False
        self.grid_size: int = 20
        self.grid_offset: int = 0
        self.show_debug_lines: bool = False
        self.setSpacing(10)

    def __del__(self) -> None:
        while self.count():
            self.takeAt(0)

    # --- Standard QLayout Overrides ---

    def addItem(self, item: QLayoutItem) -> None:  # type: ignore[override]
        self._item_list.append(item)

    def count(self) -> int:  # type: ignore[override]
        return len(self._item_list)

    def itemAt(self, index: int) -> Optional[QLayoutItem]:  # type: ignore[override]
        if 0 <= index < len(self._item_list):
            return self._item_list[index]
        return None

    def takeAt(self, index: int) -> Optional[QLayoutItem]:  # type: ignore[override]
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientation:  # type: ignore[override]
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:  # type: ignore[override]
        return True

    def heightForWidth(self, width: int) -> int:  # type: ignore[override]
        return self._do_layout(QRect(0, 0, width, 0), apply_geometry=False)

    def setGeometry(self, rect: QRect) -> None:  # type: ignore[override]
        super().setGeometry(rect)
        self._do_layout(rect, apply_geometry=True)

    def sizeHint(self) -> QSize:  # type: ignore[override]
        return self.minimumSize()

    def minimumSize(self) -> QSize:  # type: ignore[override]
        # Calculate the size of the largest child to ensure we don't crush items
        size = QSize()
        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())
        
        # Add margins
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    # --- Layout Logic ---

    def _get_alignment_point(self, item: QLayoutItem, item_height: int) -> int:
        widget = item.widget()
        if widget:
            base_point = widget.property("base_point")
            if base_point is not None and isinstance(base_point, int):
                return base_point
        return item_height // 2

    def _do_layout(self, rect: QRect, apply_geometry: bool = False) -> int:
        x = rect.x()
        y = rect.y()
        effective_width = rect.width()
        spacing = self.spacing()

        if apply_geometry:
            self._line_debug_positions.clear()

        line_items: List[QLayoutItem] = []

        def process_line(
            current_items: List[QLayoutItem], current_y: int, is_dry_run: bool
        ) -> int:
            if not current_items:
                return current_y

            max_ascent = 0
            max_descent = 0

            # 1. Measure Line Height
            for item in current_items:
                size = item.sizeHint()
                ascent = self._get_alignment_point(item, size.height())
                descent = size.height() - ascent
                max_ascent = max(max_ascent, ascent)
                max_descent = max(max_descent, descent)

            # 2. Grid Snapping
            candidate_baseline_y = current_y + max_ascent
            if self.grid_enabled and self.grid_size > 0:
                rel_y = candidate_baseline_y - self.grid_offset
                if rel_y < 0: rel_y = 0
                grid_index = (rel_y + self.grid_size - 1) // self.grid_size
                final_baseline_y = (grid_index * self.grid_size) + self.grid_offset
                while (final_baseline_y - max_ascent) < current_y:
                    final_baseline_y += self.grid_size
            else:
                final_baseline_y = candidate_baseline_y

            # 3. Position Items
            if not is_dry_run:
                self._line_debug_positions.append((final_baseline_y, effective_width))
                current_x_cursor = rect.x()
                for item in current_items:
                    size = item.sizeHint()
                    ascent = self._get_alignment_point(item, size.height())
                    item_y = final_baseline_y - ascent
                    item.setGeometry(QRect(QPoint(current_x_cursor, item_y), size))
                    current_x_cursor += size.width() + spacing

            return (final_baseline_y + max_descent) + spacing

        current_x = 0
        current_y_cursor = y
        
        for item in self._item_list:
            size = item.sizeHint()
            widget = item.widget()
            
            force_break = False
            if widget:
                force_break = widget.property("force_new_line") or False

            next_x = current_x + size.width()
            
            # Wrap Logic
            if len(line_items) > 0 and (next_x > effective_width or force_break):
                current_y_cursor = process_line(
                    line_items, current_y_cursor, not apply_geometry
                )
                line_items = []
                current_x = 0
                next_x = size.width()

            line_items.append(item)
            current_x = next_x + spacing

        if line_items:
            current_y_cursor = process_line(
                line_items, current_y_cursor, not apply_geometry
            )

        return current_y_cursor - rect.y()

    def paint_debug_visuals(self, painter: QPainter) -> None:
        if not self.show_debug_lines: return
        pen = QPen(QColor(255, 0, 0, 180))
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        for y, w in self._line_debug_positions:
            painter.drawLine(0, y, w, y)


class FlowContainer(QWidget):
    """
    A simple Widget wrapper for FlowLayout.
    It does not handle scrolling. It simply expands indefinitely.
    """

    def __init__(
        self,
        min_height: Optional[int] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        
        self._min_height = min_height

        self.flow_layout = FlowLayout(self)
        
        # We set specific size policies to ensure it behaves well in other layouts
        # Horizontal: Ignored (Try to fit parent width)
        # Vertical: Preferred (Grow as tall as needed)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    def paintEvent(self, event: QPaintEvent) -> None:  # type: ignore[override]
        super().paintEvent(event)
        painter = QPainter(self)
        self.flow_layout.paint_debug_visuals(painter)

    def minimumSizeHint(self) -> QSize:
        """Enforces the 'minimal height' property."""
        s = super().minimumSizeHint()
        if self._min_height is not None:
            return QSize(s.width(), max(s.height(), self._min_height))
        return s

    def add_widget(self, widget: QWidget) -> None:
        self.flow_layout.addWidget(widget)

    def remove_widget(self, widget: QWidget) -> None:
        self.flow_layout.removeWidget(widget)
        widget.setParent(None)  # type: ignore
        widget.deleteLater()

    def set_grid(self, enabled: bool, size: int = 20) -> None:
        self.flow_layout.grid_enabled = enabled
        self.flow_layout.grid_size = size
        self.flow_layout.invalidate()
        self.update()

    def set_debug(self, enabled: bool) -> None:
        self.flow_layout.show_debug_lines = enabled
        self.update()
