# Project TODO List

This file tracks planned features, refactors, and bug fixes for the ChannelFlow project.

## Features & Enhancements

-   **Delete Individual Thumbnails**: Implement functionality for users to delete specific generated images from the video detail page. This requires both a frontend UI element (e.g., a delete button on each image) and a backend API endpoint to handle the deletion from Firestore and GCS.

## Refactoring & Technical Debt

-   **Re-evaluate On-Demand Image Metadata**: Revisit storing rich metadata for on-demand generated images (prompt, model, timestamp, etc.). This could be crucial for implementing features like model usage tracking, cost analysis, and enforcing quotas, which is a concern for production environments. This would involve reverting the data model back to using a list of objects instead of simple strings. 