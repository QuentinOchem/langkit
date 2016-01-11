## vim: filetype=makopython

<%def name="subclass_decls(cls)">

   <%
      # Parent class for "cls", or None if "cls" is actually the root AST node
      # (if we called .base() on it, it would return ASTNode).
      parent_cls = cls.base() if ctx.root_grammar_class != cls else None

      # Python expression that yield a tuple that contains the names for all
      # fields that "cls" inherits.
      parent_fields = ('{}._field_names'.format(parent_cls.name().camel)
                       if parent_cls else
                       '()')
   %>

    _field_names = ${parent_fields} + (
        % for field in cls.fields_with_accessors():
        "${field.name.lower}",
        % endfor
    )

    % if not cls.abstract:
    _kind_name = ${repr(cls.name().camel)}
    % endif

    % for field in cls.fields_with_accessors():

    @property
    def ${field.name.lower}(self):
        ${py_doc(field, 8)}
        ## Declare a variable of the type
        result = ${pyapi.type_internal_name(field.type)}()

        ## Get it via the C field accessor
        if not _${field.accessor_basename.lower}(self._c_value,
                                                 ctypes.byref(result)):
           raise PropertyError()

        return ${pyapi.wrap_value('result', field.type)}
    % endfor
</%def>

<%def name="decl(cls)">

class ${cls.name().camel}(${cls.base().name().camel}):
    ${py_doc(cls, 4)}
${subclass_decls(cls)}

</%def>
