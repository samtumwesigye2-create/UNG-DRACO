# DRACO Power & Motion Layer

DRACO uses regulated low-voltage DC internally. Mains AC stays outside the printed sensor enclosure and enters only through a certified external power supply.

## Power path

External source -> certified isolated supply -> protected DC input -> regulated distribution -> controller and S1/S2/S3 branches.

The device heartbeat can report input voltage, current, power, battery state, source, undervoltage/overcurrent state, S1/S2/S3 branch health, and pan/tilt power health.

## Electromagnetic functions

- Transformer/isolation principle: external supply isolation and conversion; do not place exposed mains circuitry in the enclosure.
- Generator principle: future independent or backup charging source feeds the protected DC/battery subsystem.
- Motor principle: low-voltage pan/tilt or positioning actuators controlled by the existing DRACO motion-control subsystem.
- AC: restricted to the certified external power boundary.
- DC: controller, cameras, sensors, communications, USB power, batteries and actuators.

These are architecture capabilities, not assumptions that uninstalled hardware is present. Physical commissioning must confirm actual voltages, current limits, connector pinouts, actuator requirements and S1/S2/S3 devices before enabling hardware control.
