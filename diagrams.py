"""Source Dependency Tree Diagram

This feature is used to display a useful dependency tree diagram for any given source key,
in order for a user to see how any given source is built.

This feature can be broken down into three main steps:
1. For any given source key, translating the sources config into a dependency dictionary: get_source_dependency_tree()
2. Translating the dependency dictionary into a mermaid configuration file: build_source_mermaid()
3. Rendering the mermaid diagram into Streamlit (Zac's job): webapp.src.mermaid.render_mermaid()

An example dependency tree looks as follows

source_key_example:
  mapping:
    left:
      source_key1: "file"
    right:
      source_key2:
        union:
          source_key3: "file"
          source_key4: "sql"
          source_key5:
            multi:
              source_key6: "union_directory"

"""
from typing import Tuple, Optional
from webapp.src.mermaid import Flowchart, Node


def get_source_dependency_tree(sources_config: dict, source_key: str) -> dict:
    """Traverses through the sources config, and produces a source dependency tree for a given source key.

    Args:
        sources_config (dict): The source config containing all the dependent sources for the interested source.
        source_key (str): The source key that you want to see the dependencies of.

    Raises:
        KeyError: If source_key not in sources_config.
        Exception: If a source has an invalid source config.
        Excpetion: If a source has an invalid source_type.

    Returns:
        dict: Source dependency dictionary. See example at the top of the file.kz
    """

    dependency_tree = {}

    source_config = sources_config.get(source_key)
    if source_config is None:
        raise KeyError(f"The source key {source_key} was not found in the sources config.")

    source_type = source_config.get("type")
    # Complex sources are sources composed of multiple other sources
    complex_sources = ["mapping", "union", "multi"]
    if source_type not in complex_sources:
        if source_type is None:
            # Source type is not mandatory for file / sql, so type is inferred from connection config
            # TODO: Change this when config backwards compatibility is broken and source type is enforced
            config = source_config.get("connection").get("config")
            if config is None:
                # TODO: Make this a custom exception
                raise Exception("Invalid source config.")
            if "file_type" in config.keys():
                dependency_tree[source_key] = "file"
            else:
                dependency_tree[source_key] = "sql"
        elif source_type == "union_directory":
            # The only source_type that is not complex, "file" or "sql" is "union_dir"
            dependency_tree[source_key] = "union_directory"
        else:
            # TODO: Make this a custom exception
            raise Exception("Invalid source type. Must be either: sql, file, union_dir, mapping, union or multi.")
    else:
        # If source is complex, get it's constituent source keys and call get_dependency_tree again
        if source_type == "mapping":
            left_source = source_config.get("left")
            right_source = source_config.get("right")
            map_nest = {
                "left": get_source_dependency_tree(sources_config, left_source),
                "right": get_source_dependency_tree(sources_config, right_source),
            }
            dependency_tree[source_key] = {"mapping": map_nest}
        elif source_type == "union":
            sources = list(source_config["sources"].keys())
            union_nest = {}
            for union_source in sources:
                union_nest.update(get_source_dependency_tree(sources_config, union_source))
            dependency_tree[source_key] = {"union": union_nest}
        elif source_type == "multi":
            original = source_config.get("original")
            original_nest = get_source_dependency_tree(sources_config, original)
            dependency_tree[source_key] = {"multi": original_nest}

    return dependency_tree


def build_source_dependency_chart(
    chart: Flowchart, dependency_tree: dict, parent_source: Optional[Node] = None, map_right: Optional[bool] = False
) -> Flowchart:
    """Recursively build the source dependency chart from a dependency tree dict.

    Args:
        chart (Flowchart): Source dependency flowchart, either blank or partially complete.
        dependency_tree (dict): The target source's dependency tree.
        parent_source (str, optional): The parent source of the target. Defaults to None.
        map_right (bool, optional): Flag indicating if the target source is the right side of a map. Defaults to False.

    Raises:
        Exception: If an incorrect leaf source type is passed. Allowed simple types: file, sql & union_directory.
        TypeError: If a complex source doesn't have any dependency information nested underneath it.
        Exception: If an incorrect complex source type is passed. Allowed complex types: mapping, union or multi.

    Returns:
        Flowchart: Completed source dependency flowchart.
    """
    # Get source key of the top level source
    source = next(iter(dependency_tree.keys()))
    # Get the nest for the level down from the top level source
    nest = dependency_tree.get(source)

    # For leaf level sources, the nest will just be the string type of the simple source
    if isinstance(nest, str):
        # Map of leaf source types and corresponding node shape
        leaf_node_map = {"file": "[]", "sql": "[()]", "union_directory": "[[]]"}
        try:
            source_node = Node(source, leaf_node_map[nest])
        except KeyError as error:
            # TODO: Make this a custom exception
            raise Exception(
                "Leaf level sources should have one of the following types: file, sql & union_directory"
            ) from error
        chart.add_node(source_node)
        if parent_source is not None:
            if map_right:
                chart.add_path(source_node, parent_source, path_style="-.->")
            else:
                chart.add_path(source_node, parent_source)

        return chart

    if not isinstance(nest, dict):
        raise TypeError("Invalid simple source type or complex source without information on its children?")

    # All other source nests should be of type dict
    # Error handling of above
    source_node = Node(source, "{{}}")
    chart.add_node(source_node)
    if parent_source is not None:
        chart.add_path(source_node, parent_source)
    if "mapping" in nest.keys():
        mapping_tree = nest.get("mapping")
        left_tree = mapping_tree.get("left")
        build_source_dependency_chart(chart, left_tree, source_node)
        # TODO: Don't hardcode this map_right behaviour, what about FOJ or ROJ?
        right_tree = mapping_tree.get("right")
        build_source_dependency_chart(chart, right_tree, source_node, map_right=True)
    elif "union" in nest.keys():
        union_nest = nest.get("union")
        for source_key, source_nest in union_nest.items():
            source_dict = {}
            source_dict[source_key] = source_nest
            build_source_dependency_chart(chart, source_dict, source_node)
    elif "multi" in nest.keys():
        multi_nest = nest.get("multi")
        build_source_dependency_chart(chart, multi_nest, source_node)
    else:
        # TODO: Make this a custom exception
        raise Exception("Dependency dict error. Complex sources should have type: mapping, union or multi.")

    return chart


def get_source_mermaid_key() -> Tuple[str, str]:
    """Creates the diagrammatic key that allows the user to interpret the diagram.

    Returns:
        Tuple[str, str]:
            node_mermaid: A key showing which source types maps to which node types.
            path_mermaid: A key showing how different complex source builds are represented.
    """
    # Nodes
    node_chart = Flowchart()
    file_node = Node("File source", "[]")
    sql_node = Node("SQL source", "[()]")
    union_dir_node = Node("Union of a directory", "[[]]")
    combined_node = Node("Combined source", "{{}}")
    node_chart.add_nodes([file_node, sql_node, union_dir_node, combined_node])

    # Paths
    path_chart = Flowchart()
    # Mapping
    map_source = Node("Mapped source", "{{}}")
    file_left = Node("File source left", "[]")
    sql_right = Node("SQL source right", "[()]")
    path_chart.add_nodes([map_source, file_left, sql_right])
    path_chart.add_path(file_left, map_source)
    path_chart.add_path(sql_right, map_source, path_style="-.->")

    # Union
    union_source = Node("Unioned source", "{{}}")
    ud_union = Node("Union directory", "[[]]")
    sql_union = Node("SQL", "[()]")
    path_chart.add_nodes([union_source, ud_union, sql_union])
    path_chart.add_path(ud_union, union_source)
    path_chart.add_path(sql_union, union_source)

    # Multi
    multi_source = Node("Multi source", "{{}}")
    original = Node("Original SQL source", "[()]")
    path_chart.add_nodes([multi_source, original])
    path_chart.add_path(original, multi_source)

    # Convert charts to mermaid
    node_mermaid = node_chart.to_mermaid()
    path_mermaid = path_chart.to_mermaid()

    return node_mermaid, path_mermaid


def get_source_mermaid(sources_config: dict, source_key: str) -> str:
    """Creates a source dependency mermaid config for a given source key.

    Args:
        sources_config (dict): The source config containing all the dependent sources for the interested source.
        source_key (str): The source key that you want to see the dependencies of.

    Returns:
        str: source dependency mermaid config
    """

    dependency_tree = get_source_dependency_tree(sources_config, source_key)
    dependency_chart = build_source_dependency_chart(chart=Flowchart(), dependency_tree=dependency_tree)
    dependency_mermaid = dependency_chart.to_mermaid()
    return dependency_mermaid
