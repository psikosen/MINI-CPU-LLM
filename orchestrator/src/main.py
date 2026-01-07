#!/usr/bin/env python3
"""
Main entry point for orchestrator
"""

import argparse
import logging
import sys
import yaml
from pathlib import Path

from orchestrator import Orchestrator


def setup_logging(debug: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if debug else logging.INFO

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('/tmp/orchestrator.log')
        ]
    )


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            return config or {}
    except FileNotFoundError:
        logging.warning(f"Config file not found: {config_path}")
        return {}
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        return {}


def main():
    parser = argparse.ArgumentParser(description='Voice Assistant Orchestrator')
    parser.add_argument('--config', '-c', default='/etc/voice_assistant/config.yaml',
                       help='Path to configuration file')
    parser.add_argument('--debug', '-d', action='store_true',
                       help='Enable debug logging')
    parser.add_argument('--dev', action='store_true',
                       help='Development mode (use local config)')

    args = parser.parse_args()

    # Setup logging
    setup_logging(debug=args.debug or args.dev)
    logger = logging.getLogger(__name__)

    logger.info("=" * 50)
    logger.info("Voice Assistant Orchestrator v1.0.0")
    logger.info("=" * 50)

    # Load config
    if args.dev:
        config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    else:
        config_path = args.config

    config = load_config(str(config_path))
    logger.info(f"Loaded configuration from {config_path}")

    # Create and start orchestrator
    try:
        orchestrator = Orchestrator(config)

        if not orchestrator.start():
            logger.error("Failed to start orchestrator")
            sys.exit(1)

        # Run main loop
        orchestrator.run()

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

    logger.info("Orchestrator shutdown complete")


if __name__ == "__main__":
    main()
