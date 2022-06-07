"""The mermaid module provides the Node and Flowchart classes, as well as a rend_mermaid function for rendering
diagrams in streamlit. A Flowchart can have Nodes added to it, which are then joined by paths.

Example Usage:
    # Create Nodes
    start = Node("Start").set_shape("rounded")
    middle = Node("Middle")
    end = Node("End").set_shape("stadium")
    print(start, middle, end)  # We can look at the Node definitions

    # Add nodes to the flowchart
    chart = Flowchart()
    chart.add_nodes([start, middle, end])

    print(chart)
"""
from __future__ import annotations
from typing import Iterable, List
import itertools
import streamlit.components.v1 as components


class Node:
    """The Node class is used to define Nodes that can later be added to a Flowchart. Attirbutes such as label, shape
    and style can be added to each Node."""

    id_iter = itertools.count(100)

    def __init__(self, label: str, shape: str = "[]", style: str = None) -> None:
        self.label = label
        self.node_id = str(next(self.id_iter))
        self.shape = shape
        self.style = style
        self.shape_map = {
            "rounded": r"()",
            "stadium": r"([])",
            "subroutine": r"[[]]",
            "cylinder": r"[()]",
            "circle": r"(())",
            "asymmetric": r">]",
            "rhombus": r"{}",
            "hexagon": r"{{}}",
            "parallelogram": r"[//]",
            "parallelogram_alt": r"[\\]",
            "trapezoid": r"[/\]",
            "trapezoid_alt": r"[\/]",
        }

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(id={self.node_id}, label={self.label}, shape={self.shape}, style={self.style})"
        )

    def set_style(
        self, fill: str = None, stroke: str = None, stroke_width: int = None, stroke_dasharray: Iterable[int] = None
    ) -> Node:
        """Sets the style of a node.

        Args:
            fill (str, optional): The hex fill colour for a node. Defaults to None.
            stroke (str, optional): The hex stroke colour. Defaults to None.
            stroke_width (int, optional): The border thickness. Defaults to None.
            stroke_dasharray (Iterable(int)): The array of border dash options. Defaults to None.

        Returns:
            Node: Returns the node itself.
        """
        style = f"style {self.node_id}"
        if fill:
            style += f" fill:{fill},"
        if stroke:
            style += f" stroke:{stroke},"
        if stroke_width:
            style += f" stroke-width:{stroke_width}px,"
        if stroke_dasharray:
            stringified = (str(val) for val in stroke_dasharray)
            style += f" stroke-dasharray: {' '.join(stringified)},"
        self.style = style[:-1]
        return self

    def set_shape(self, shape_name: str) -> Node:
        """Sets the shape of the node.

        Args:
            shape_name (str): The name of the string. Options: rounded, stadium, subroutine, cylinder, circle,
                asymmetric, rhombus, hexagon, parallelogram, parallelogram_alt, trapezoid, trapezoid_alt.

        Raises:
            KeyError: Raised if a shape that isn't available is selected.

        Returns:
            Node: The Node itself. This allows stringing of methods.
        """
        try:
            shape = self.shape_map[shape_name]
        except KeyError as shape_no_exist:
            option_list = ", ".join(self.shape_map.keys())
            raise KeyError(f"{shape_name} does not exist. Available options are: {option_list}") from shape_no_exist
        self.shape = shape
        return self

    def set_shape_raw(self, shape_str: str) -> Node:
        """Sets the shape of the node using a the mermaid delimiters.

        Args:
            shape_str (str): The string of up to four characters that create the node shape.

        Raises:
            Exception: Raised if the shape characters aren't valid mermaid shapes.

        Returns:
            Node: The Node itself. This allows stringing of methods.
        """
        if shape_str not in self.shape_map.values():
            options_list = ", ".join(self.shape_map.values())
            raise Exception(f"Shape string {shape_str} is not valid. Valid options are: {options_list}")
        self.shape = shape_str
        return self

    def get_node_code(self) -> str:
        """Returns the string of Mermaid code to define the node.

        Returns:
            str: The string of Mermaid code defining the node.
        """
        shape_midpoint = int(len(self.shape) / 2)
        return f"""\n{self.node_id}{self.shape[:shape_midpoint]}{self.label}{self.shape[shape_midpoint:]}"""


class Flowchart:
    """The Flowchart class creates a mermaid flow diagram by accepting Nodes, and definitions of paths between the
    nodes."""

    def __init__(self, orientation="TD", theme="default") -> None:
        self.orientation = orientation
        self.theme = theme
        self.nodes = []
        self.paths = []
        self.hrefs = {}
        self.clicks = {}

    def __repr__(self) -> str:
        return self.to_mermaid()

    def add_node(self, node: Node) -> None:
        """Adds a Node object to the flowchart.

        Args:
            node (Node): The Node to be added to the flowchart.
        """
        self.nodes.append(node)

    def add_nodes(self, node_list: List[Node]) -> None:
        """Adds a list of Nodes to the flowchart.

        Args:
            node_list (List[Node]): The list of Nodes to be added to the flowchart.
        """
        self.nodes += node_list

    def add_path(self, start_node: Node, end_node: Node, label: str = "", path_style: str = "-->") -> None:
        """Adds a path between two nodes.

        Args:
            start_node (str): The Node to start the path from.
            end_node_label (str): The Node to end the path at.
            path_label (str, optional): The label to add to the path. Defaults to empty string.
            path_style (str, optional): The style of the path. Defaults to -->.
        """
        if label != "":
            label = f"|{label}|"
        self.paths.append(f"""\n{start_node.node_id} {path_style}{label}{end_node.node_id}""")

    def add_href_click(self, node: Node, click_value: str, tooltip: str = "_blank") -> None:
        """Adds a click action to a node.

        Args:
            node_id (str): The id of the node to add the click action to.
            click_type (str): The type of click to add: href, callback.
            click_value (str): The value of the option. This could be a url for href or a function for callback.
            tooltip (str, optional): The tooltip to display if required. Defaults to None.
        """
        if tooltip != "_blank":
            tooltip = f""""{tooltip}" _blank"""
        self.hrefs[node] = f"""\nclick {node.node_id} "{click_value}" {tooltip}"""

    def add_fn_click(self, node: Node, click_value: str, tooltip: str = " ") -> None:
        """Adds a js function call to a node.

        Args:
            node_id (str): The id of the node to add the click action to.
            click_value (str): The value of the option. This could be a url for href or a function for callback.
            tooltip (str, optional): The tooltip to display if required. Defaults to None.
        """
        self.clicks[node] = f"""\nclick {node.node_id} call {click_value} "{tooltip}" """

    def to_mermaid(self) -> str:
        """Converts the Flowchart attributes to Mermaid code.

        Returns:
            str: A Mermaid flowchart as a string.
        """
        mermaid = f"graph {self.orientation}"

        # Define nodes
        for node in self.nodes:
            mermaid += node.get_node_code().strip(" ")
            if node.style is not None:
                mermaid += "\n" + node.style.strip(" ")

        # Define paths between nodes
        for path in self.paths:
            mermaid += path.strip(" ")

        # Define clicks
        for click in self.clicks.values():
            mermaid += click.strip(" ")

        # Define hrefs
        for href in self.hrefs.values():
            mermaid += href.strip(" ")

        return mermaid


def render_mermaid(mermaid: str, height: int = 150, width: int = None, scrolling: bool = False) -> None:
    """Renders a mermaid diagram.

    Args:
        mermaid (str): The mermaid code for the diagram.
        height (int): The height of the frame in CSS pixels. Defaults to 150.
        width (int): The width of the frame in CSS pixels. Defaults to the report’s default element width.
        scrolling (bool): If True, show a scrollbar when the content is larger than the iframe. Defaults to False.
    """
    components.html(
        f"""
        <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
        <div class="mermaid">
        {mermaid}
        </div>
        """,
        height=height,
        width=width,
        scrolling=scrolling,
    )
