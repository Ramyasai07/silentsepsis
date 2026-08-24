# SilentSepsis Flutter Frontend

A Flutter-based clinical monitoring dashboard for the SilentSepsis project.

## Overview

The Flutter frontend provides a desktop interface for monitoring patients, viewing sepsis risk, managing alerts, and analyzing ward-level information.

## Features

- Patient monitoring dashboard
- Patient details and vital history
- Sepsis risk scores and risk levels
- Alert management
- Ward monitoring
- Risk and alert analytics
- Backend API configuration
- Demo patient dataset for presentation

## Frontend Structure

- `lib/screens/` - Application screens
- `lib/widgets/` - Reusable UI components
- `lib/models/` - Patient, alert, vital and risk models
- `lib/repositories/` - Data access layer
- `lib/services/` - API and configuration services
- `lib/theme/` - Application styling and risk colors
- `lib/data/` - Demo presentation data

## Backend Integration

The Flutter application communicates with the SilentSepsis FastAPI backend through REST APIs.

The API provides patient, alert, ward, vital and prediction data.

## Running the Application

```bash
flutter pub get
flutter analyze
flutter run -d windows
