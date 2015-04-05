#!/bin/bash

#set -x

rm -rfv ~/rpmbuild
rpmdev-setuptree ~

sourceurl=$( python -c "import rpm; spec = rpm.spec('fedora-gooey-karma.spec'); print spec.sources[0][0]")
echo "Source: $sourceurl"
pushd ~/rpmbuild/SOURCES
wget "$sourceurl"
popd
rpmbuild -ba fedora-gooey-karma.spec


#set +x
