%global commit 2fd265f7987da757b28db9d9dc11e7db9119d14e
%global shortcommit %(c=%{commit}; echo ${c:0:7})

Name:           fedora-gooey-karma
Version:        0.1
Release:        2%{?dist}
Summary:        GUI tool for sending feedback about installed Test Update packages

Group:          Development/Tools
License:        GPLv3+
URL:            https://fedoraproject.org/wiki/Fedora_Gooey_Karma

Source0:        https://github.com/blaskovic/fedora-gooey-karma/archive/%{commit}/%{name}-%{version}-%{shortcommit}.tar.gz
BuildArch:      noarch

BuildRequires:  desktop-file-utils
BuildRequires:  python2-devel

Requires:       python-fedora
Requires:       fedora-cert
Requires:       yum
Requires:       yum-utils
Requires:       bodhi-client
Requires:       python-pyside
Requires:       python-keyring
Requires:       koji

%description
Fedora-gooey-karma helps you to easily and fast provide feedback for all testing
updates that you have currently installed and browse the available ones. It is
similar tool to fedora-easy-karma but with graphical front-end.

%prep
%setup -q -n %{name}-%{commit}

%build

%post
/bin/touch --no-create %{_datadir}/icons/hicolor &>/dev/null || :

%postun
if [ $1 -eq 0 ] ; then
    /bin/touch --no-create %{_datadir}/icons/hicolor &>/dev/null
    /usr/bin/gtk-update-icon-cache %{_datadir}/icons/hicolor &>/dev/null || :
fi

%posttrans
/usr/bin/gtk-update-icon-cache %{_datadir}/icons/hicolor &>/dev/null || :

%install
make install DESTDIR=%{buildroot} BINDIR=%{_bindir} DATADIR=%{_datadir}
desktop-file-validate %{buildroot}/%{_datadir}/applications/fedora-gooey-karma.desktop

%files
%doc COPYING
%{_bindir}/%{name}
%{_datadir}/%{name}
%{_datadir}/applications/%{name}.desktop
%{_datadir}/icons/hicolor/*/apps/%{name}.png

%changelog
* Mon Dec 9 2013 Branislav Blaskovic <branislav@blaskovic.sk> - 0.1-2
- python2-devel added as build requires
- removed deletion of buildroot dir

* Fri Oct 18 2013 Branislav Blaskovic <branislav@blaskovic.sk> - 0.1-1
- Initial spec file
