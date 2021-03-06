"""
Test that automatic default values are provided for Then expressions that
return analysis units.
"""

from __future__ import absolute_import, division, print_function

from langkit.dsl import ASTNode, T, has_abstract_list
from langkit.expressions import Property, Self

from utils import build_and_run


class FooNode(ASTNode):
    node_unit = Property(
        Self.cast(T.Name).then(lambda n: n.unit),
        public=True
    )


@has_abstract_list
class Name(FooNode):
    token_node = True


class Scope(Name.list):
    pass


build_and_run(lkt_file='expected_concrete_syntax.lkt', py_script='main.py')
print('Done')
