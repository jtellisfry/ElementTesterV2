"""
Settings Manager
=================

Manages application settings stored in JSON config file.
Provides load/save functionality for relay driver selection.

Config file location: src/element_tester/system/core/instrument_configuration.json
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional
import json
import logging


@dataclass
class AppSettings:
    """Application settings configuration."""
    relay_driver: str = "MCC_ERB"  # Options: "MCC_ERB" or "MCC_PDIS"
    meter_driver: str = "FLUKE287"  # Options: "FLUKE287" or "UT61E"
    
    # Relay driver specific parameters
    erb08_board_num: int = 0
    erb08_port_low: int = 12
    erb08_port_high: int = 13
    
    pdis08_board_num: int = 1
    pdis08_port_low: int = 1
    pdis08_port_high: Optional[int] = None
    
    # Meter driver specific parameters
    # Fluke 287 params
    fluke_port: str = "COM11"
    fluke_timeout: float = 2.0
    
    # UT61E params (HID)
    ut61e_com_port: str = "COM12"
    ut61e_vendor_id: int = 0x1a86
    ut61e_product_id: int = 0xe429
    ut61e_serial_number: Optional[str] = None


class SettingsManager:
    """
    Manages loading and saving application settings.
    
    Settings are stored in system/core/instrument_configuration.json
    """
    
    DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "core" / "instrument_configuration.json"
    
    def __init__(self, config_path: Optional[Path] = None, logger: Optional[logging.Logger] = None):
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.log = logger or logging.getLogger("element_tester.settings")
    
    def load(self) -> AppSettings:
        """
        Load settings from JSON file.
        
        Returns:
            AppSettings instance with loaded values or defaults if file doesn't exist
        """
        if not self.config_path.exists():
            self.log.info(f"Config file not found at {self.config_path}, using defaults")
            return AppSettings()
        
        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)
            
            settings = AppSettings(**data)
            settings.relay_driver = self._normalize_relay_driver(settings.relay_driver)
            self.log.info(f"Settings loaded: relay_driver={settings.relay_driver}")
            return settings
            
        except Exception as e:
            self.log.error(f"Failed to load settings from {self.config_path}: {e}", exc_info=True)
            self.log.info("Using default settings")
            return AppSettings()
    
    def save(self, settings: AppSettings) -> bool:
        """
        Save settings to JSON file.
        
        Args:
            settings: AppSettings instance to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create config directory if it doesn't exist
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to dict and save
            data = asdict(settings)
            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=4)
            
            self.log.info(f"Settings saved to {self.config_path}: relay_driver={settings.relay_driver}")
            return True
            
        except Exception as e:
            self.log.error(f"Failed to save settings to {self.config_path}: {e}", exc_info=True)
            return False
    
    def get_relay_driver_choice(self) -> str:
        """
        Get the currently configured relay driver.
        
        Returns:
            "MCC_ERB" or "MCC_PDIS"
        """
        settings = self.load()
        return settings.relay_driver
    
    def set_relay_driver_choice(self, driver: str) -> bool:
        """
        Set the relay driver choice and save.
        
        Args:
            driver: "MCC_ERB" or "MCC_PDIS"
            
        Returns:
            True if successful, False otherwise
        """
        if driver not in ["MCC_ERB", "MCC_PDIS"]:
            self.log.error(f"Invalid relay driver choice: {driver}")
            return False
        
        settings = self.load()
        settings.relay_driver = driver
        return self.save(settings)

    def _normalize_relay_driver(self, driver: str) -> str:
        """Normalize legacy relay driver names to current values."""
        if driver == "ERB08":
            return "MCC_ERB"
        if driver == "PDIS08":
            return "MCC_PDIS"
        return driver


def get_relay_driver_from_config(config_path: Optional[Path] = None) -> str:
    """
    Convenience function to get relay driver choice from config.
    
    Args:
        config_path: Optional custom config path
        
    Returns:
        "MCC_ERB" or "MCC_PDIS"
    """
    manager = SettingsManager(config_path)
    return manager.get_relay_driver_choice()


def get_meter_driver_from_config(config_path: Optional[Path] = None) -> str:
    """
    Convenience function to get meter driver choice from config.
    
    Args:
        config_path: Optional custom config path
        
    Returns:
        "FLUKE287" or "UT61E"
    """
    manager = SettingsManager(config_path)
    settings = manager.load()
    return settings.meter_driver


def get_meter_params_from_config(config_path: Optional[Path] = None) -> AppSettings:
    """
    Return full AppSettings (including meter params) loaded from config.
    
    This is useful for consumers that need driver-specific params.
    
    Args:
        config_path: Optional custom config path
        
    Returns:
        AppSettings instance with all configuration
    """
    manager = SettingsManager(config_path)
    return manager.load()
