import json
import unittest


class BaseNode(object):

    """
    Interface class for implicit and excplicit nodes.
    """

    def add_edge(self, position):
        """
        Performs adding a new edge for letter at position `position` in the original string to the node.
        Returns tuple (operation_type, new_node).
        Operation type could be 1 (an edge is being added to a leaf node), 2 (an edge is being newly added to an
        internal node) or 3 (an edge is not added because it already exists).
        """
        raise NotImplementedError()

    def trace_string(self, start, end=None):
        raise NotImplementedError()

    @property
    def suffix_link(self):
        raise NotImplementedError()


class Node(BaseNode):

    """
    Excplicit node (one that either has several children or is a leaf node).
    """

    def __init__(self, string, parent_node, edge_start, edge_end=None):
        self.string = string
        self.parent_node = parent_node
        self.edge_start = edge_start
        self.edge_end = edge_end or len(string)
        self.edges = {}
        self._suffix_link = None
        self.is_root = False

    def add_edge(self, position):
        letter = self.string[position]
        if letter in self.edges:
            # Type 3: nothing to do
            operation_type = 3
        elif self.edges or self.is_root:
            # Type 2: added a new edge
            self.edges[letter] = Node(self.string, self, position)
            operation_type = 2
        else:
            # Type 1: leaf node, extended automatically
            operation_type = 1

        return operation_type, self.trace_string(position)

    def _get_suffix_link(self):
        if not self._suffix_link:
            self._suffix_link = self._calculate_suffix_link()

        return self._suffix_link

    def _set_suffix_link(self, node):
        self._suffix_link = node

    suffix_link = property(_get_suffix_link, _set_suffix_link)

    def _calculate_suffix_link(self):
        parent_suffix_link = self.parent_node.suffix_link

        if parent_suffix_link is None:
            # Only possible if parent node is a root node
            suffix_link = self.parent_node.trace_string(self.edge_start + 1, self.edge_end)
        else:
            suffix_link = parent_suffix_link.trace_string(self.edge_start, self.edge_end)

        return suffix_link

    def trace_string(self, start, end=None):
        end = end or start + 1
        if start == end:
            return self

        letter = self.string[start]
        edge = self.edges[letter]
        if end - start >= edge.length:
            return edge.trace_string(start + edge.length, end)
        else:
            return ImplicitNode(edge, edge.edge_start + end - start)

    def search_string(self, pattern):
        """
        This method in contrast to `trace_string` performs search of a pattern and doesn't rely on the fact that pattern
        exists in the tree (it may not exist as well).
        """
        if not pattern:
            return True

        letter = pattern[0]
        if letter not in self.edges:
            return False

        edge = self.edges[letter]

        pattern_chunk = pattern[:edge.length]
        edge_chunk = self.string[edge.edge_start:edge.edge_end][:len(pattern)]

        if pattern_chunk == edge_chunk:
            if len(pattern) >= edge.length:
                return edge.search_string(pattern[edge.length:])
            return True
        return False

    @property
    def length(self):
        return self.edge_end - self.edge_start

    def serialize(self):
        children = {}
        for child in self.edges.itervalues():
            children.update(child.serialize())

        serialized = {
            self.string[self.edge_start:self.edge_end]: children,
        }

        return serialized

    def __str__(self):
        return '%s (%s) --> %s' % (str(self.parent_node),
                                   ', '.join(self.parent_node.edges.keys()),
                                   self.string[self.edge_start:self.edge_end])

    def __repr__(self):
        return self.__str__()


class RootNode(Node):

    """
    Special root node.
    """

    def __init__(self, string):
        super(RootNode, self).__init__(string, None, 0, 0)
        self.edge_end = 0
        self.is_root = True

    @property
    def suffix_link(self):
        return None

    def serialize(self):
        serialized = super(RootNode, self).serialize()
        serialized = serialized['']
        return serialized

    def __str__(self):
        return 'ROOT'


class ImplicitNode(BaseNode):

    """
    Implicit node (a node that lies in the middle of an edge. Implicit nodes are not stored in the tree, that means
    that explicit nodes never refer to implicit.
    Note that `self.node` is a successor of `self`, not a predecessor;
    `position` is not the length between this implicit node and the edge start, but a position of a string which must
    be between `self.node.edge_start` and `self.node.edge_end` (not inclusively).
    """

    def __init__(self, node, position):
        self.node = node
        self.position = position
        self.is_root = False

    def add_edge(self, position):
        letter = self.node.string[position]
        next_letter = self.node.string[self.position]

        if letter == next_letter:
            if self.node.edges or self.position < position:  # Internal node
                # Type 3: nothing to do
                operation_type = 3
            else:
                # Type 1: nothing to do because of leaf node
                operation_type = 1

            if self.node.edge_end - self.position == 1:
                return operation_type, self.node
            return operation_type, ImplicitNode(self.node, self.position + 1)
        else:
            # Split the edge
            predecessor = self.node.parent_node
            ancestor = self.node

            middle_node = Node(self.node.string, predecessor, ancestor.edge_start, self.position)
            predecessor.edges[self.node.string[middle_node.edge_start]] = middle_node

            ancestor.edge_start = self.position
            ancestor.parent_node = middle_node
            middle_node.edges[next_letter] = self.node

            # Add new edge
            new_node = Node(self.node.string, middle_node, position)
            middle_node.edges[letter] = new_node

            return 2, middle_node.trace_string(position)  # Type 2: added a new edge

    @property
    def suffix_link(self):
        parent_suffix_link = self.node.parent_node.suffix_link

        if parent_suffix_link is None:
            assert isinstance(self.node.parent_node, RootNode)
            suffix_link = self.node.parent_node.trace_string(self.node.edge_start + 1, self.position)

        else:
            suffix_link = parent_suffix_link.trace_string(self.node.edge_start, self.position)

        return suffix_link

    def trace_string(self, start, end=None):
        end = end or start + 1
        if start - end < self.node.edge_end - self.position:
            return ImplicitNode(self.node, self.position + end - start)
        else:
            return self.node.trace_string(start + self.node.edge_end - self.position, end)


class Ukkonen(object):
    def __init__(self, string):
        root_node = RootNode(string)

        current_node = root_node
        for i in xrange(len(string)):
            while True:
                operation_type, new_node = current_node.add_edge(i)

                if operation_type == 3 or current_node.is_root:
                    current_node = new_node
                    break

                current_node = current_node.suffix_link

        self.tree = root_node

    def search(self, pattern):
        return self.tree.search_string(pattern)


class TestUkkonen(unittest.TestCase):
    def setUp(self):
        self.ukkonen = Ukkonen('mississippi')
        print json.dumps(self.ukkonen.tree.serialize(), indent=4)

    def test(self):
        self.assertTrue(self.ukkonen.search('issi'))
        self.assertTrue(self.ukkonen.search('issip'))
        self.assertTrue(self.ukkonen.search('mi'))
        self.assertTrue(self.ukkonen.search('mississippi'))
        self.assertTrue(self.ukkonen.search(''))
        self.assertFalse(self.ukkonen.search('pississ'))
        self.assertFalse(self.ukkonen.search('issisi'))
        self.assertFalse(self.ukkonen.search('mississippis'))


if __name__ == '__main__':
    unittest.main()
