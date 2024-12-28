# This file is derived from https://github.com/apptainer/singularity/blob/9dceb4240c12b4cff1da94630d422a3422b39fcf/internal/pkg/build/sources/base_environment.go#L286

import os
import stat
import logging
from pathlib import Path


def make_dirs(root_path):
    try:
        (Path(root_path) / ".singularity.d/libs").mkdir(parents=True, exist_ok=True)
        (Path(root_path) / ".singularity.d/actions").mkdir(parents=True, exist_ok=True)
        (Path(root_path) / ".singularity.d/env").mkdir(parents=True, exist_ok=True)
        (Path(root_path) / "dev").mkdir(parents=True, exist_ok=True)
        (Path(root_path) / "proc").mkdir(parents=True, exist_ok=True)
        (Path(root_path) / "root").mkdir(parents=True, exist_ok=True)
        (Path(root_path) / "var/tmp").mkdir(parents=True, exist_ok=True)
        (Path(root_path) / "tmp").mkdir(parents=True, exist_ok=True)
        (Path(root_path) / "etc").mkdir(parents=True, exist_ok=True)
        (Path(root_path) / "sys").mkdir(parents=True, exist_ok=True)
        (Path(root_path) / "home").mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logging.error(f"Error creating directories: {e}")
        raise


def make_symlinks(root_path):
    try:
        symlinks = {
            "singularity": ".singularity.d/runscript",
            ".run": ".singularity.d/actions/run",
            ".exec": ".singularity.d/actions/exec",
            ".test": ".singularity.d/actions/test",
            ".shell": ".singularity.d/actions/shell",
            "environment": ".singularity.d/env/90-environment.sh",
        }
        for link, target in symlinks.items():
            link_path = Path(root_path) / link
            target_path = Path(root_path) / target
            if not link_path.exists():
                link_path.symlink_to(target_path)
    except Exception as e:
        logging.error(f"Error creating symlinks: {e}")
        raise


def make_file(name, content, perm):
    try:
        file_path = Path(name)
        if file_path.exists():
            file_path.chmod(perm)
        with open(file_path, "w") as f:
            f.write(content)
        file_path.chmod(perm)
    except Exception as e:
        logging.error(f"Error creating file {name}: {e}")
        raise


def make_files(root_path):
    try:
        file_contents = {
            "etc/hosts": "",
            "etc/resolv.conf": "",
            ".singularity.d/actions/exec": execFileContent,
            ".singularity.d/actions/run": runFileContent,
            ".singularity.d/actions/shell": shellFileContent,
            ".singularity.d/actions/start": startFileContent,
            ".singularity.d/actions/test": testFileContent,
            ".singularity.d/env/01-base.sh": baseShFileContent,
            ".singularity.d/env/90-environment.sh": environmentShFileContent,
            ".singularity.d/env/95-apps.sh": appsShFileContent,
            ".singularity.d/env/99-base.sh": base99ShFileContent,
            ".singularity.d/env/99-runtimevars.sh": base99runtimevarsShFileContent,
            ".singularity.d/runscript": runscriptFileContent,
            ".singularity.d/startscript": startscriptFileContent,
        }
        for file, content in file_contents.items():
            make_file(Path(root_path) / file, content, 0o755)
    except Exception as e:
        logging.error(f"Error creating files: {e}")
        raise


def make_base_env(root_path):
    try:
        root = Path(root_path)
        if not os.access(root, os.W_OK):
            root.chmod(root.stat().st_mode | stat.S_IWUSR)
        make_dirs(root_path)
        make_symlinks(root_path)
        make_files(root_path)
    except Exception as e:
        logging.error(f"Error setting up base environment: {e}")
        raise


# Replace these with actual file content from the Go code
execFileContent = r"""#!/bin/sh

for script in /.singularity.d/env/*.sh; do
    if [ -f "$script" ]; then
        . "$script"
    fi
done

exec "$@"
"""
runFileContent = r"""#!/bin/sh

for script in /.singularity.d/env/*.sh; do
    if [ -f "$script" ]; then
        . "$script"
    fi
done

if test -n "${SINGULARITY_APPNAME:-}"; then

    if test -x "/scif/apps/${SINGULARITY_APPNAME:-}/scif/runscript"; then
        exec "/scif/apps/${SINGULARITY_APPNAME:-}/scif/runscript" "$@"
    else
        echo "No Singularity runscript for contained app: ${SINGULARITY_APPNAME:-}"
        exit 1
    fi

elif test -x "/.singularity.d/runscript"; then
    exec "/.singularity.d/runscript" "$@"
else
    echo "No Singularity runscript found, executing /bin/sh"
    exec /bin/sh "$@"
fi
"""
shellFileContent = r"""#!/bin/sh

for script in /.singularity.d/env/*.sh; do
    if [ -f "$script" ]; then
        . "$script"
    fi
done

if test -n "$SINGULARITY_SHELL" -a -x "$SINGULARITY_SHELL"; then
    exec $SINGULARITY_SHELL "$@"

    echo "ERROR: Failed running shell as defined by '\$SINGULARITY_SHELL'" 1>&2
    exit 1

elif test -x /bin/bash; then
    SHELL=/bin/bash
    PS1="Singularity $SINGULARITY_NAME:\\w> "
    export SHELL PS1
    exec /bin/bash --norc "$@"
elif test -x /bin/sh; then
    SHELL=/bin/sh
    export SHELL
    exec /bin/sh "$@"
else
    echo "ERROR: /bin/sh does not exist in container" 1>&2
fi
exit 1
"""
startFileContent = r"""#!/bin/sh

# if we are here start notify PID 1 to continue
# DON'T REMOVE
kill -CONT 1

for script in /.singularity.d/env/*.sh; do
    if [ -f "$script" ]; then
        . "$script"
    fi
done

if test -x "/.singularity.d/startscript"; then
    exec "/.singularity.d/startscript"
fi
"""
testFileContent = r"""#!/bin/sh

for script in /.singularity.d/env/*.sh; do
    if [ -f "$script" ]; then
        . "$script"
    fi
done


if test -n "${SINGULARITY_APPNAME:-}"; then

    if test -x "/scif/apps/${SINGULARITY_APPNAME:-}/scif/test"; then
        exec "/scif/apps/${SINGULARITY_APPNAME:-}/scif/test" "$@"
    else
        echo "No tests for contained app: ${SINGULARITY_APPNAME:-}"
        exit 1
    fi
elif test -x "/.singularity.d/test"; then
    exec "/.singularity.d/test" "$@"
else
    echo "No test found in container, executing /bin/sh -c true"
    exec /bin/sh -c true
fi
"""
baseShFileContent = r"""#!/bin/sh
# 
# Copyright (c) 2017, SingularityWare, LLC. All rights reserved.
# Copyright (c) 2015-2017, Gregory M. Kurtzer. All rights reserved.
# 
# Copyright (c) 2016-2017, The Regents of the University of California,
# through Lawrence Berkeley National Laboratory (subject to receipt of any
# required approvals from the U.S. Dept. of Energy).  All rights reserved.
# 
# This software is licensed under a customized 3-clause BSD license.  Please
# consult LICENSE.md file distributed with the sources of this project regarding
# your rights to use or distribute this software.
# 
# NOTICE.  This Software was developed under funding from the U.S. Department of
# Energy and the U.S. Government consequently retains certain rights. As such,
# the U.S. Government has been granted for itself and others acting on its
# behalf a paid-up, nonexclusive, irrevocable, worldwide license in the Software
# to reproduce, distribute copies to the public, prepare derivative works, and
# perform publicly and display publicly, and to permit other to do so.
# 
# 
"""
environmentShFileContent = r"""#!/bin/sh
# Custom environment shell code should follow
"""
appsShFileContent = r"""#!/bin/sh
#
# Copyright (c) 2017, SingularityWare, LLC. All rights reserved.
#
# See the COPYRIGHT.md file at the top-level directory of this distribution and at
# https://github.com/hpcng/singularity/blob/master/COPYRIGHT.md.
#
# This file is part of the Singularity Linux container project. It is subject to the license
# terms in the LICENSE.md file found in the top-level directory of this distribution and
# at https://github.com/hpcng/singularity/blob/master/LICENSE.md. No part
# of Singularity, including this file, may be copied, modified, propagated, or distributed
# except according to the terms contained in the LICENSE.md file.


if test -n "${SINGULARITY_APPNAME:-}"; then

    # The active app should be exported
    export SINGULARITY_APPNAME

    if test -d "/scif/apps/${SINGULARITY_APPNAME:-}/"; then
        SCIF_APPS="/scif/apps"
        SCIF_APPROOT="/scif/apps/${SINGULARITY_APPNAME:-}"
        export SCIF_APPROOT SCIF_APPS
        PATH="/scif/apps/${SINGULARITY_APPNAME:-}:$PATH"

        # Automatically add application bin to path
        if test -d "/scif/apps/${SINGULARITY_APPNAME:-}/bin"; then
            PATH="/scif/apps/${SINGULARITY_APPNAME:-}/bin:$PATH"
        fi

        # Automatically add application lib to LD_LIBRARY_PATH
        if test -d "/scif/apps/${SINGULARITY_APPNAME:-}/lib"; then
            LD_LIBRARY_PATH="/scif/apps/${SINGULARITY_APPNAME:-}/lib:$LD_LIBRARY_PATH"
            export LD_LIBRARY_PATH
        fi

        # Automatically source environment
        if [ -f "/scif/apps/${SINGULARITY_APPNAME:-}/scif/env/01-base.sh" ]; then
            . "/scif/apps/${SINGULARITY_APPNAME:-}/scif/env/01-base.sh"
        fi
        if [ -f "/scif/apps/${SINGULARITY_APPNAME:-}/scif/env/90-environment.sh" ]; then
            . "/scif/apps/${SINGULARITY_APPNAME:-}/scif/env/90-environment.sh"
        fi

        export PATH
    else
        echo "Could not locate the container application: ${SINGULARITY_APPNAME}"
        exit 1
    fi
fi
"""
base99ShFileContent = r"""#!/bin/sh
# 
# Copyright (c) 2017, SingularityWare, LLC. All rights reserved.
# Copyright (c) 2015-2017, Gregory M. Kurtzer. All rights reserved.
# 
# Copyright (c) 2016-2017, The Regents of the University of California,
# through Lawrence Berkeley National Laboratory (subject to receipt of any
# required approvals from the U.S. Dept. of Energy).  All rights reserved.
# 
# This software is licensed under a customized 3-clause BSD license.  Please
# consult LICENSE.md file distributed with the sources of this project regarding
# your rights to use or distribute this software.
# 
# NOTICE.  This Software was developed under funding from the U.S. Department of
# Energy and the U.S. Government consequently retains certain rights. As such,
# the U.S. Government has been granted for itself and others acting on its
# behalf a paid-up, nonexclusive, irrevocable, worldwide license in the Software
# to reproduce, distribute copies to the public, prepare derivative works, and
# perform publicly and display publicly, and to permit other to do so.
# 
# 


if [ -z "$LD_LIBRARY_PATH" ]; then
    LD_LIBRARY_PATH="/.singularity.d/libs"
else
    LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/.singularity.d/libs"
fi

PS1="Singularity> "
export LD_LIBRARY_PATH PS1
"""
base99runtimevarsShFileContent = r"""#!/bin/sh
# Copyright (c) 2017-2019, Sylabs, Inc. All rights reserved.
#
# This software is licensed under a customized 3-clause BSD license.  Please
# consult LICENSE.md file distributed with the sources of this project regarding
# your rights to use or distribute this software.
#
#

if [ -n "${SING_USER_DEFINED_PREPEND_PATH:-}" ]; then
	PATH="${SING_USER_DEFINED_PREPEND_PATH}:${PATH}"
fi

if [ -n "${SING_USER_DEFINED_APPEND_PATH:-}" ]; then
	PATH="${PATH}:${SING_USER_DEFINED_APPEND_PATH}"
fi

if [ -n "${SING_USER_DEFINED_PATH:-}" ]; then
	PATH="${SING_USER_DEFINED_PATH}"
fi

unset SING_USER_DEFINED_PREPEND_PATH \
	  SING_USER_DEFINED_APPEND_PATH \
	  SING_USER_DEFINED_PATH

export PATH
"""
runscriptFileContent = r"""#!/bin/sh

echo "There is no runscript defined for this container\n";
"""
startscriptFileContent = r"""#!/bin/sh
"""
