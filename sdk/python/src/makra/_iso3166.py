"""ISO 3166-1 alpha-2 country codes for proxy egress targeting.

``config.crawler.proxy.region.value`` is an ISO 3166-1 alpha-2 code when
``scope`` is ``country``. This module is the SDK's named mapping for those
codes, analogous to :class:`~makra._constants.ValidationModes`.
"""

from __future__ import annotations

from typing import FrozenSet

# Officially assigned ISO 3166-1 alpha-2 codes, plus XK (Kosovo, commonly
# used by proxy providers even though it is user-assigned).
ISO_3166_ALPHA2_CODES: FrozenSet[str] = frozenset(
    """
    AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ
    BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ
    CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CY CZ
    DE DJ DK DM DO DZ
    EC EE EG EH ER ES ET
    FI FJ FK FM FO FR
    GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY
    HK HM HN HR HT HU
    ID IE IL IM IN IO IQ IR IS IT
    JE JM JO JP
    KE KG KH KI KM KN KP KR KW KY KZ
    LA LB LC LI LK LR LS LT LU LV LY
    MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ
    NA NC NE NF NG NI NL NO NP NR NU NZ
    OM
    PA PE PF PG PH PK PL PM PN PR PS PT PW PY
    QA
    RE RO RS RU RW
    SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ
    TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ
    UA UG UM US UY UZ
    VA VC VE VG VI VN VU
    WF WS
    XK
    YE YT
    ZA ZM ZW
    """.split()
)


class Iso3166Alpha2:
    """ISO 3166-1 alpha-2 country codes.

    Use as ``config.crawler.proxy.region.value`` when the region scope is
    ``country``::

        from makra import Iso3166Alpha2, ProxyRegionScopes

        region = {"scope": ProxyRegionScopes.COUNTRY, "value": Iso3166Alpha2.DE}
    """


for _code in sorted(ISO_3166_ALPHA2_CODES):
    setattr(Iso3166Alpha2, _code, _code)

del _code
