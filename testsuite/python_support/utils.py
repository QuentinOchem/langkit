from __future__ import absolute_import, division, print_function

import os
import os.path as P
import shutil
import subprocess
import sys

import langkit
import langkit.compile_context
from langkit.compile_context import CompileCtx, UnparseScript
from langkit.diagnostics import DiagnosticError, Diagnostics, WarningSet
from langkit.libmanage import ManageScript

from testsuite_support.valgrind import valgrind_cmd


Diagnostics.blacklisted_paths.append(P.dirname(P.abspath(__file__)))


default_warning_set = WarningSet()

# We don't want to be forced to provide dummy docs for nodes and public
# properties in testcases.
default_warning_set.disable(WarningSet.undocumented_nodes)
default_warning_set.disable(WarningSet.undocumented_public_properties)

pretty_print = bool(int(os.environ.get('LANGKIT_PRETTY_PRINT', '0')))

project_template = """
with "libfoolang";

project Gen is
    for Languages use ("Ada");
    for Source_Dirs use (".");
    for Object_Dir use "obj";
    for Main use ({main_sources});

    package Compiler is
        for Default_Switches ("Ada") use
          ("-g", "-O0", "-gnata", "-gnatwae", "-gnatyg");
    end Compiler;
end Gen;
"""


valgrind_enabled = bool(os.environ.get('VALGRIND_ENABLED'))


# Determine where to find the root directory for Langkit sources
langkit_root = os.environ.get('LANGKIT_ROOT_DIR')
if not langkit_root:
    test_dir = P.dirname(P.abspath(__file__))
    testsuite_dir = P.dirname(test_dir)
    langkit_root = P.dirname(testsuite_dir)


# When unparsing the concrete syntax, name of the file to write
unparse_destination = 'concrete_syntax.lkt'
unparse_script = ('to:{},import:lexer_example,grammar,nodes'
                  .format(unparse_destination))
unparse_all_script = 'to:{},lexer,grammar,nodes'.format(unparse_destination)


def prepare_context(grammar=None, lexer=None, lkt_file=None,
                    warning_set=default_warning_set,
                    symbol_canonicalizer=None, show_property_logging=False):
    """
    Create a compile context and prepare the build directory for code
    generation.

    :param langkit.parsers.Grammar grammar: The language grammar to use for
        this context.

    :param langkit.lexer.Lexer lexer: The language lexer to use for this
        context.

    :param str|None lkt_file: If provided, file from which to read the Lkt
        language spec.

    :param WarningSet warning_set: Set of warnings to emit.

    :param langkit.compile_context.LibraryEntity|None symbol_canonicalizer:
        Symbol canonicalizer to use for this context, if any.

    :param bool show_property_logging: See CompileCtx.show_property_logging.
    """

    # Have a clean build directory
    if P.exists('build'):
        shutil.rmtree('build')
    os.mkdir('build')

    # Try to emit code
    ctx = CompileCtx(lang_name='Foo', short_name='Foo', lexer=lexer,
                     grammar=grammar,
                     symbol_canonicalizer=symbol_canonicalizer,
                     show_property_logging=show_property_logging,
                     lkt_file=lkt_file)
    ctx.warnings = warning_set
    ctx.pretty_print = pretty_print

    return ctx


def emit_and_print_errors(grammar=None, lexer=None, lkt_file=None,
                          warning_set=default_warning_set,
                          generate_unparser=False, symbol_canonicalizer=None,
                          unparse_script=None):
    """
    Compile and emit code for CTX. Return the compile context if this was
    successful, None otherwise.

    :param langkit.parsers.Grammar grammar_fn: The language grammar to use.

    :param langkit.lexer.Lexer lexer: The lexer to use along with the grammar.
        Use `lexer_example.foo_lexer` if left to None.

    :param str|None lkt_file: If provided, file from which to read the Lkt
        language spec.

    :param WarningSet warning_set: Set of warnings to emit.

    :param bool generate_unparser: Whether to generate unparser.

    :param langkit.compile_context.LibraryEntity|None symbol_canonicalizer:
        Symbol canoncalizes to use for this context, if any.

    :rtype: None|langkit.compile_context.CompileCtx

    :param None|str unparse_script: Script to unparse the language spec.
    """

    try:
        ctx = prepare_context(grammar, lexer, lkt_file, warning_set,
                              symbol_canonicalizer=symbol_canonicalizer)
        ctx.emit('build', generate_unparser=generate_unparser,
                 unparse_script=(UnparseScript(unparse_script)
                                 if unparse_script else None))
        # ... and tell about how it went
    except DiagnosticError:
        # If there is a diagnostic error, don't say anything, the diagnostics
        # are enough.
        return None
    else:
        print('Code generation was successful')
        return ctx
    finally:
        if lexer is not None:
            lexer._dfa_code = None
        langkit.reset()


def build(grammar=None, lexer=None, lkt_file=None,
          warning_set=default_warning_set, mains=False):
    """
    Shortcut for `build_and_run` to only build.
    """
    build_and_run(grammar=grammar, lexer=lexer, lkt_file=lkt_file,
                  warning_set=warning_set)


def build_and_run(grammar=None, py_script=None, ada_main=None, lexer=None,
                  lkt_file=None, ocaml_main=None,
                  warning_set=default_warning_set, generate_unparser=False,
                  symbol_canonicalizer=None, mains=False,
                  show_property_logging=False, unparse_script=unparse_script):
    """
    Compile and emit code for `ctx` and build the generated library. Then,
    execute the provided scripts/programs, if any.

    An exception is raised if any step fails (the script must return code 0).

    :param langkit.lexer.Lexer lexer: The lexer to use along with the grammar.
        See emit_and_print_errors.

    :param str|None lkt_file: If provided, file from which to read the Lkt
        language spec.

    :param None|str py_script: If not None, name of the Python script to run
        with the built library available.

    :param None|str|list[str] ada_main: If not None, list of name of main
        source files for Ada programs to build and run with the generated
        library. If the input is a single string, consider it's a single mail
        source file.

    :param None|str ocaml_main: If not None, name of the OCaml source file to
        build and run with the built library available.

    :param WarningSet warning_set: Set of warnings to emit.

    :param bool generate_unparser: Whether to generate unparser.

    :param langkit.compile_context.LibraryEntity|None symbol_canonicalizer:
        Symbol canonicalizer to use for this context, if any.

    :param bool mains: Whether to build mains.

    :param bool show_property_logging: If true, any property that has been
        marked with tracing activated will be traced on stdout by default,
        without need for any config file.

    :param None|str unparse_script: Script to unparse the language spec.
    """

    ctx = prepare_context(grammar, lexer, lkt_file, warning_set,
                          symbol_canonicalizer=symbol_canonicalizer,
                          show_property_logging=show_property_logging)

    class Manage(ManageScript):
        def create_context(self, args):
            return ctx

    m = Manage()

    extensions_dir = P.abspath('extensions')
    if P.isdir(extensions_dir):
        ctx.extensions_dir = extensions_dir

    # First build the library. Forward all test.py's arguments to the libmanage
    # call so that manual testcase runs can pass "-g", for instance. Also avoid
    # rebuilding Langkit_Support, as the testsuite already built one for us.
    argv = sys.argv[1:] + ['--full-error-traces', '-vnone',
                           '--no-langkit-support']

    # Generate the public Ada API only when necessary (i.e. if we have mains
    # that do use this API). This reduces the time it takes to run tests.
    if not mains and not ada_main:
        argv.append('--no-ada-api')

    argv.append('make')

    build_mode = 'dev'
    argv.append('--build-mode={}'.format(build_mode))
    for w in WarningSet.available_warnings:
        argv.append('-{}{}'.format('W' if w in warning_set else 'w', w.name))
    if not pretty_print:
        argv.append('--no-pretty-print')
    if generate_unparser:
        argv.append('--generate-unparser')

    # For testsuite performance, do not generate mains unless told otherwise
    if not mains:
        argv.append('--disable-all-mains')

    # RA22-015: Unparse the language to concrete syntax
    if unparse_script:
        argv.append('--unparse-script')
        argv.append(unparse_script)

    m.run(argv)

    # Flush stdout and stderr, so that diagnostics appear deterministically
    # before the script/program output.
    sys.stdout.flush()
    sys.stderr.flush()

    # Write a "setenv" script to make developper investigation convenient
    with open('setenv.sh', 'w') as f:
        m.write_setenv(build_mode, f)

    env = m.derived_env(build_mode)

    def run(*argv, **kwargs):
        valgrind = kwargs.pop('valgrind', False)
        suppressions = kwargs.pop('valgrind_suppressions', [])
        assert not kwargs

        if valgrind_enabled and valgrind:
            argv = valgrind_cmd(list(argv), suppressions)

        subprocess.check_call(argv, env=env)

    if py_script is not None:
        # Run the Python script. Note that in order to use the generated
        # library, we have to use the special Python interpreter the testsuite
        # provides us. See the corresponding code in
        # testuite_support/python_driver.py.
        python_interpreter = os.environ['PYTHON_INTERPRETER']
        run(python_interpreter, py_script)

    if ada_main is not None:
        if isinstance(ada_main, str):
            ada_main = [ada_main]

        # Generate a project file to build the given Ada main and then run
        # the program.
        with open('gen.gpr', 'w') as f:
            f.write(project_template.format(
                main_sources=', '.join('"{}"'.format(m) for m in ada_main)
            ))
        run('gprbuild', '-Pgen', '-q', '-p',
            '-XLIBRARY_TYPE=relocatable', '-XXMLADA_BUILD=relocatable')

        for i, m in enumerate(ada_main):
            assert m.endswith('.adb')
            if i > 0:
                print('')
            if len(ada_main) > 1:
                print('== {} =='.format(m))
            sys.stdout.flush()
            run(P.join('obj', m[:-4]), valgrind=True)

    if ocaml_main is not None:
        # Set up a Dune project
        with open('dune', 'w') as f:
            f.write("""
                (executable
                  (name {})
                  (flags (-w -9))
                  (libraries {}))
            """.format(ocaml_main, ctx.c_api_settings.lib_name))
        with open('dune-project', 'w') as f:
            f.write('(lang dune 1.6)')

        # Build the ocaml executable
        run('dune', 'build', '--display', 'quiet', '--root', '.',
            './{}.exe'.format(ocaml_main))

        # Run the ocaml executable
        run('./_build/default/{}.exe'.format(ocaml_main),
            valgrind=True,
            valgrind_suppressions=['ocaml'])


def add_gpr_path(dirname):
    """
    Prepend the given directory name to the ``GPR_PROJECT_PATH`` environment
    variable.
    """
    old_path = os.environ.get('GPR_PROJECT_PATH')
    os.environ['GPR_PROJECT_PATH'] = (
        '{}{}{}'.format(dirname, P.pathsep, old_path)
        if old_path else dirname)
