from PyQt6.QtWidgets import QScrollArea, QWidget, QFrame
from PyQt6.QtCore import Qt
# Import the sacred code
from flow_layout import FlowContainer 

class ScrollableFlow(QScrollArea):
    """
    A view that renders a tiny part of the infinite FlowContainer.
    It handles the scrollbars and clipping.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 1. Setup the Infinite Widget
        self._container = FlowContainer()
        
        # 2. Setup the Scroll Area
        # This is the magic command. It forces the container to fit the width.
        self.setWidgetResizable(True) 
        
        self.setWidget(self._container)
        
        # Visual cleanup
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        
        # Scrollbar policies
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    # --- Proxy Methods ---
    # We expose the FlowContainer's API through this wrapper
    
    def add_widget(self, widget: QWidget):
        self._container.add_widget(widget)

    def remove_widget(self, widget: QWidget):
        self._container.remove_widget(widget)

    def set_grid(self, enabled: bool, size: int = 20):
        self._container.set_grid(enabled, size)

    def set_debug(self, enabled: bool):
        self._container.set_debug(enabled)

    def container(self) -> FlowContainer:
        """Access the inner sacred widget if needed."""
        return self._container
