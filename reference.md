# 38770-K03-H01

64 KiB Honda PGM-FI. Model code ASCII `K03S10A`. Definition: `38770-K03-H01.toml` (XDF XML → `romtool xdf2toml`). Other bikes: user gives unlocked XDF XML if no TOML.

Shared map axes (fuel + ignition):

| Axis | Addr | n | Units | Breakpoints |
|---|---|---|---|---|
| RPM (Y) | `0x10` | 29 | RPM | 840, 1100, 1200, 1300, 1400, 1500, 1600, 1800, 2000, 2250, 2500, 2750, 3000, 3250, 3500, 4000, 4500, 5000, 5500, 6000, 6500, 7000, 7500, 7750, 8000, 8500, 9000, 9500, 9800 |
| Load (X) | `0x4A` | 25 | Load % | 0, 0.5, 1, 1.5, 2.6, 3.3, 4, 4.6, 5.2, 6.5, 7.8, 10.5, 13, 15.7, 18.3, 21, 24.5, 27.6, 34.8, 41.9, 52.2, 58.9, 66, 78.2, 95 |

Row 0 = 840 RPM, col 0 = 0 load. `shape = [rows=RPM, cols=load]`.

## Tables

| Key | Title | Shape | Real units (stock range) | Notes |
|---|---|---|---|---|
| `fuel_calcurated_load_map` | Fuel Calcurated Load Map | 29×25 u2 | raw ~607–10040 | Keep spelling. Stock values match `fuel_base_map`; different address (`0x7C` vs `0x626`). Edit both if user wants “all fuel”. |
| `fuel_base_map` | Fuel Base Map | 29×25 u2 | raw ~607–10040 | Relative scale only. Not ms, not AFR. |
| `ignition_map_1` | Ignition Map 1 | 29×25 u1 | deg ~6–71 (`*0.351563-14`) | Condition vs map 2 unknown. Do not guess gear/ECT. |
| `ignition_map_2` | Ignition Map 2 | 29×25 u1 | deg ~6–68 | Same. |
| `fuel_rev_limiter` | Fuel Rev Limiter | 1×2 u2 | RPM ~9600, 9800 | Labels Low, High. Fuel cut. Example patched → ~10500, 10550. |
| `ignition_rev_limiter` | Ignition Rev Limiter | 1×2 u2 | RPM ~11800, 11600 | Labels High, Low (order ≠ fuel). Stock sits above fuel cut. |
| `engine_temp_sensor_scaling` | ECT scaling | 1×10 u1 | °C = raw-40 | Sensor curve. Do not “tune” for power. |
| `iat_temp_sensor_scaling` | IAT scaling | 1×10 u1 | °C = raw-40 | Same. |
| `flag_bit_setting` | Flag Bit Setting | 1×6 u1 | raw | Prefer named `[flags.*]` over this blob. |
| `model_code` | Model Code | 1×8 u1 | ASCII | Identify ROM. Do not patch. |

TOML `categories` are noisy (fuel tagged Ignition, sensors tagged RPM Limiter). Trust **title + key**, not category.

## Flags

tinyrom does not read these. romtool does. Address + mask from TOML.

| Key | Default stock (this bin) | Danger |
|---|---|---|
| `eot_sensor_enable` | on | |
| `tp_sensor_enable` | on | |
| `iat_sensor_enable` | on | |
| `o2_sensor_enable` | on | Pair with `o2_feedback_enable` |
| `injector_enable` | on | Hard no to disable |
| `eeprom_enable` | on | |
| `bank_angle_sensor_enable` | on | Hard no to disable |
| `ltft_disable` | off | TOML: if disable, disable O2 too |
| `o2_feedback_enable` | on | Closed loop |

## Example patched.bin

4 bytes. Only `fuel_rev_limiter` cells changed. All maps/flags otherwise identical to ori. Workflow check: `diff` must show that one table, `changed_cells=2`.
