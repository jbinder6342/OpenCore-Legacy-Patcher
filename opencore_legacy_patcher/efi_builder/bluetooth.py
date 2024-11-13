"""
bluetooth.py: Class for handling Bluetooth Patches, invocation from build.py
"""

import logging
import binascii

from . import support

from .. import constants

from ..detections import device_probe

from ..datasets import (
    cpu_data,
    smbios_data,
    bluetooth_data
)


class BuildBluetooth:
    """
    Build Library for Bluetooth Support

    Invoke from build.py
    """

    def __init__(self, model: str, global_constants: constants.Constants, config: dict) -> None:
        self.model: str = model
        self.config: dict = config
        self.constants: constants.Constants = global_constants
        self.computer: device_probe.Computer = self.constants.computer

        self._build()


    def _build(self) -> None:
        """
        Kick off Bluetooth Build Process
        """

        if not self.constants.custom_model and self.computer.bluetooth_chipset:
            self._on_model()
        else:
            self._prebuilt_assumption()


    def _bluetooth_firmware_incompatibility_workaround(self) -> None:
        """
        For Mac firmwares that are unable to perform firmware uploads.
        Namely Macs with BCM2070 and BCM2046 chipsets, as well as pre-2012 Macs with upgraded chipsets.
        """
        self.config["NVRAM"]["Add"]["7C436110-AB2A-4BBB-A880-FE41995C9F82"]["bluetoothInternalControllerInfo"] = binascii.unhexlify("0000000000000000000000000000")
        self.config["NVRAM"]["Add"]["7C436110-AB2A-4BBB-A880-FE41995C9F82"]["bluetoothExternalDongleFailed"] = binascii.unhexlify("00")
        self.config["NVRAM"]["Delete"]["7C436110-AB2A-4BBB-A880-FE41995C9F82"] += ["bluetoothInternalControllerInfo", "bluetoothExternalDongleFailed"]
        logging.info("- bluetooth_firmware_incompatibility_workaround set.")

    def _on_model(self) -> None:
        """
        On-Model Hardware Detection Handling
        """
        if self.computer.bluetooth_chipset in ["BRCM2070 Hub", "BRCM2046 Hub"]:
            logging.info("- on_model() -- Fixing Legacy Bluetooth for macOS Monterey (BRCM2070 Hub, BRCM2046 Hub)")
            support.BuildSupport(self.model, self.constants, self.config).enable_kext("BlueToolFixup.kext", self.constants.bluetool_version, self.constants.bluetool_path)
            support.BuildSupport(self.model, self.constants, self.config).enable_kext("Bluetooth-Spoof.kext", self.constants.btspoof_version, self.constants.btspoof_path)
            self.config["NVRAM"]["Add"]["7C436110-AB2A-4BBB-A880-FE41995C9F82"]["boot-args"] += " -btlfxallowanyaddr"
            self._bluetooth_firmware_incompatibility_workaround()
        elif self.computer.bluetooth_chipset == "BRCM20702 Hub":
            logging.info("- _on_model() BRCM20702 Hub found")
            # BCM94331 can include either BCM2070 or BRCM20702 v1 Bluetooth chipsets
            # Note Monterey only natively supports BRCM20702 v2 (found with BCM94360)
            # Due to this, BlueToolFixup is required to resolve Firmware Uploading on legacy chipsets
            if self.computer.wifi:
                logging.info("- _on_model() -- computer.wifi")

                if self.computer.wifi.chipset == device_probe.Broadcom.Chipsets.AirPortBrcm4360:
                    logging.info("- _on_model() -- Fixing Legacy Bluetooth for macOS Monterey(AirPortBrcm4360)")
                    support.BuildSupport(self.model, self.constants, self.config).enable_kext("BlueToolFixup.kext", self.constants.bluetool_version, self.constants.bluetool_path)

            # Older Mac firmwares (pre-2012) don't support the new chipsets correctly (regardless of WiFi card)
            if self.model in smbios_data.smbios_dictionary:
                if smbios_data.smbios_dictionary[self.model]["CPU Generation"] < cpu_data.CPUGen.ivy_bridge.value:
                    logging.info("- Fixing Legacy Bluetooth for macOS Monterey")
                    support.BuildSupport(self.model, self.constants, self.config).enable_kext("BlueToolFixup.kext", self.constants.bluetool_version, self.constants.bluetool_path)
                    self._bluetooth_firmware_incompatibility_workaround()
        elif self.computer.bluetooth_chipset in ["3rd Party Bluetooth 4.0 Hub", "Generic"]:
            logging.info("- on_model() -- Detected 3rd Party Bluetooth Chipset/Generic")
            support.BuildSupport(self.model, self.constants, self.config).enable_kext("BlueToolFixup.kext", self.constants.bluetool_version, self.constants.bluetool_path)
            logging.info("- on_model() -- Enabling Bluetooth FeatureFlags")
            self.config["Kernel"]["Quirks"]["ExtendBTFeatureFlags"] = True


    def _prebuilt_assumption(self) -> None:
        """
        Fall back to pre-built assumptions
        """

        if not self.model in smbios_data.smbios_dictionary:
            return
        if not "Bluetooth Model" in smbios_data.smbios_dictionary[self.model]:
            return

        if smbios_data.smbios_dictionary[self.model]["Bluetooth Model"] <= bluetooth_data.bluetooth_data.BRCM20702_v1.value:
            logging.info("- Fixing Legacy Bluetooth for macOS Monterey")
            support.BuildSupport(self.model, self.constants, self.config).enable_kext("BlueToolFixup.kext", self.constants.bluetool_version, self.constants.bluetool_path)
            if smbios_data.smbios_dictionary[self.model]["Bluetooth Model"] <= bluetooth_data.bluetooth_data.BRCM2070.value:
                self.config["NVRAM"]["Add"]["7C436110-AB2A-4BBB-A880-FE41995C9F82"]["boot-args"] += " -btlfxallowanyaddr"
                self._bluetooth_firmware_incompatibility_workaround()
                support.BuildSupport(self.model, self.constants, self.config).enable_kext("Bluetooth-Spoof.kext", self.constants.btspoof_version, self.constants.btspoof_path)
