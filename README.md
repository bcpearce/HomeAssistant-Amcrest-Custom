# HomeAssistant Amcrest Custom Integration

Amcrest integration to replace default legacy integration.

This project is a work in progress.

![test coverage](./coverage.svg)

## Installation

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=bcpearce&repository=homeassistant-amcrest-custom&category=Integration)

### From HACS

The easiest way to install is to add the repository as a custom repository to HACS. Once installed, restart Home Assistant to enable.

### Manual

Copy the contents of `custom_components/amcrest` into the `config/custom_components` of your Home Assistant integration. Once installed, restart Home Assistant to enable.

## Why replace the default integration?

The default integration is considered "legacy". It has not been updated recently and only supports setup through YAML.

This project modernizes the setup to allow configuration through the GUI and autodetection on the network.  Features for the camera are automatically determined by polling the camera capabilities and creating the relevant entities.

## Setup

### Zeroconf

Amcrest devices support Zeroconf setup using mDNS. This is the simplest way to set up a device. If a device is on the same network as your Home Assistant instance, it can be autodetected.  Select "Add" for the detected devices and you will be prompted to enter a username and password to connect.

### Manual

If it is not detected automatically, you can manually set up a device using a URL or IP Address.

When using this method, the URL should include the scheme and port, (if different from the default 80 and 443 for http and https respectively).  This should be the same URL used to access the local webserver for the device.

If using an IP address, it is best to use a static IP, or DHCP address reservation.

### Authentication

Authentication is handled using a username and password.  This integration does not require admin privileges, so it is recommended to create a new regular user for use with this integration.

## Entities

### Camera

One camera entity will be setup for the main stream and each substream. It supports the following features:

- Camera On/Off (Privacy Mode)
- Enable/Disable motion detection
- Snapshot
- RTSP stream (newer versions of Home Assistant automatically use WebRTC)

### Binary Sensor

- Motion Detection (when enabled on the camera stream)

### Sensor

PTZ position is provided for each supported Axis:
- Pan
- Tilt
- Zoom

### Select

- PTZ Preset

### Switch

- Privacy Mode
- Smart Tracking (PTZ follows detected movement)
