# This file is part of the sos project: https://github.com/antonioromito/rhsm-api-client
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

try:
    from rhsm.RHSMClient import main
except KeyboardInterrupt:
    raise SystemExit()

if __name__ == '__main__':
    main()
