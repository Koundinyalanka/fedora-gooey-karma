# Fedora Gooey Karma

fedora-gooey-karma provides similar functionality to the fedora-easy-karma via GUI. It also currently provides some extra info like: dnf info, bodhi info, test cases, bugs.

## Based on

    http://tirfa.com/gooey-karma.html


## Dependencies

    python-fedora
    fedora-cert
    dnf
    bodhi-client
    python-pyside
    python-keyring
    koji
    
To install these dependencies, use this command:

    dnf install python-fedora fedora-cert bodhi-client python-pyside python-keyring koji
    
## Installation and usage

### Clone the repo
    
    git clone https://github.com/regeciovad/fedora-gooey-karma.git
    cd fedora-gooey-karma
    
### Run the application

The easiest way to run application is to type:
    
    make run
    
You can also run the script without Makefile:

    ./src/fedora-gooey-karma
    
### Installation to filesystem

If you decide to install application to filesystem, use install phase from Makefile:

    make install
    
### Building rpm package on Fedora

You are able to build your own RPM package on Fedora. All you need to do is to run [this](https://github.com/blaskovic/fedora-gooey-karma/blob/master/fedora-package/build_rpm.sh) script.

Please review this script before to adjust paths of rpmbuild and so.

## Authors
    
    Branislav Blaskovic <branislav@blaskovic.sk>
    Tomas Meszaros <exo@tty.sk>
    Dominika Regeciova <regeciovad@gmail.com>
    
## Blog

You can read about development on [my personal blog](https://blaskovicbranislav.wordpress.com/tag/fedora-gooey-karma/).
    
## Questions?

You can contact me via IRC Brano@freenode.org.

## Contribute

I would appreciate any idea/patch. Feel free to request any functionality.
