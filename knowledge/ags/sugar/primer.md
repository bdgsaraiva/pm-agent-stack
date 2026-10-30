# Primer: sugar

This file holds method and sources only. Live levels come from the pack.

## Contracts and prices
- **ICE raw sugar No. 11 (SB=F)**: US cents per pound, world raw cane sugar FOB. Yahoo continuous front month (personal use only).
- Brazil's Centre-South dominates world exports. The harvest runs April-November; mills split cane between sugar and ethanol on relative returns (ethanol parity with gasoline, the real). Indian and Thai crops (monsoon-dependent) and Indian export policy are the other big swings (general knowledge, not page-checked).
- UNICA's biweekly crush reports are the key Brazilian data; only the latest PDF is online, so nothing is stored (S4 source check). ANP's Brazil fuel sales (S1, `anp:sales_m3:*`) are ethanol-demand context.

## Balance
- WASDE's US sugar (#16, a protected domestic market: not #11) and PSD's world sugar (semi-annual, agent 9).
- No US report playbook: WASDE days show no extra volatility for #11 (`events.md`).
- Long run: World Bank world sugar price from 1960, deflated (`estimates/longrun.json` via the pack).
- CFTC sugar No. 11 (080732).
