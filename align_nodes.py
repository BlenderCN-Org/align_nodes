import bpy
from bpy.types import Operator, Panel, Menu
from bpy.props import FloatProperty, EnumProperty, BoolProperty, IntProperty, StringProperty, FloatVectorProperty, \
    CollectionProperty
from copy import copy
from mathutils import Vector
from glob import glob


def nw_check(context):
    space = context.space_data
    valid_trees = ["ShaderNodeTree", "CompositorNodeTree", "TextureNodeTree"]

    valid = False
    if space.type == 'NODE_EDITOR' and space.node_tree is not None and space.tree_type in valid_trees:
        valid = True

    return valid


def get_nodes_links(context):
    tree = context.space_data.node_tree

    # Get nodes from currently edited tree.
    # If user is editing a group, space_data.node_tree is still the base level (outside group).
    # context.active_node is in the group though, so if space_data.node_tree.nodes.active is not
    # the same as context.active_node, the user is in a group.
    # Check recursively until we find the real active node_tree:
    if tree.nodes.active:
        while tree.nodes.active != context.active_node:
            tree = tree.nodes.active.node_tree

    return tree.nodes, tree.links


class NWBase:
    @classmethod
    def poll(cls, context):
        return nw_check(context)


class AlignNodes(Operator, NWBase):
    '''Align the selected nodes neatly in a row/column'''
    bl_idname = "node.align_nodes"
    bl_label = "Align Nodes"
    bl_options = {'REGISTER', 'UNDO'}
    margin = IntProperty(name='Margin', default=50, description='The amount of space between nodes')

    def execute(self, context):
        nodes, links = get_nodes_links(context)
        margin = self.margin

        selection = []
        for node in nodes:
            if node.select and node.type != 'FRAME':
                selection.append(node)

        # ---------------------------------------------------------------------
        for node in selection:
            node.width_hidden = 150
            node.width = node.bl_width_default
            node.height = node.bl_height_default
        # ---------------------------------------------------------------------

        # If no nodes are selected, align all nodes
        active_loc = None
        if not selection:
            selection = nodes
        elif nodes.active in selection:
            active_loc = copy(nodes.active.location)  # make a copy, not a reference

        # Check if nodes should be layed out horizontally or vertically
        x_locs = [n.location.x + (n.dimensions.x / 2) for n in
                  selection]  # use dimension to get center of node, not corner
        y_locs = [n.location.y - (n.dimensions.y / 2) for n in selection]
        x_range = max(x_locs) - min(x_locs)
        y_range = max(y_locs) - min(y_locs)
        mid_x = (max(x_locs) + min(x_locs)) / 2
        mid_y = (max(y_locs) + min(y_locs)) / 2
        horizontal = x_range > y_range

        # Sort selection by location of node mid-point
        if horizontal:
            selection = sorted(selection, key=lambda n: n.location.x + (n.dimensions.x / 2))
        else:
            selection = sorted(selection, key=lambda n: n.location.y - (n.dimensions.y / 2), reverse=True)

        # Alignment
        current_pos = 0
        for node in selection:
            current_margin = margin
            current_margin = current_margin * 0.5 if node.hide else current_margin  # use a smaller margin for hidden nodes

            if horizontal:
                node.location.x = current_pos
                current_pos += current_margin + node.dimensions.x
                # -----------------------------------------------------------------------
                # node.location.y = mid_y + (node.dimensions.y / 2)
                node.location.y = mid_y
                # -----------------------------------------------------------------------
            else:
                node.location.y = current_pos
                current_pos -= (current_margin * 0.3) + node.dimensions.y  # use half-margin for vertical alignment
                # -----------------------------------------------------------------------
                # node.location.x = mid_x - (node.dimensions.x / 2)
                node.location.x = mid_x
                # -----------------------------------------------------------------------

        # If active node is selected, center nodes around it
        if active_loc is not None:
            active_loc_diff = active_loc - nodes.active.location
            for node in selection:
                node.location += active_loc_diff
        else:  # Position nodes centered around where they used to be
            locs = ([n.location.x + (n.dimensions.x / 2) for n in selection]) if horizontal else (
                [n.location.y - (n.dimensions.y / 2) for n in selection])
            new_mid = (max(locs) + min(locs)) / 2
            for node in selection:
                if horizontal:
                    node.location.x += (mid_x - new_mid)
                else:
                    node.location.y += (mid_y - new_mid)

        return {'FINISHED'}
