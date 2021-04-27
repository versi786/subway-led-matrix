#!/bin/bash
# From https://github.com/riffnshred/nhl-led-scoreboard/blob/master/scripts/install.sh


# Make script work regardless of where it is run from
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "${DIR}/.." || exit

echo "$(tput setaf 6)Installing required dependencies. This may take some time (10-20 minutes-ish)...$(tput setaf 9)"
#Install all apt requirements using aptfile
sudo scripts/aptfile apt-requirements

#Install all pip3 requirements using the requirements.txt filer
sudo pip3 install -r requirements.txt

# Pull submodule and ignore changes from script
git submodule update --init --recursive
git config submodule.matrix.ignore all

cd submodules/matrix || exit
echo "$(tput setaf 4)Running rgbmatrix installation...$(tput setaf 9)"

make build-python PYTHON="$(which python3)"
sudo make install-python PYTHON="$(which python3)"
cd bindings || exit
sudo pip3 install --force-reinstall -e python/

cd ../../../ || exit

git reset --hard
git fetch origin --prune
git pull

make
echo "If you didn't see any errors above, everything should be installed!"
echo "$(tput bold)$(tput smso)$(tput setaf 2)Installation complete!$(tput sgr0) Play around with the examples in ./submodules/matrix/bindings/python/samples to make sure your matrix is working."
