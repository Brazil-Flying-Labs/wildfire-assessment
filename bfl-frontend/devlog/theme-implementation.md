# Theme Implementation

## 2025-02-28
- [x] Research shadcn theming approach
- [x] Create global.css with theme variables
- [x] Implement three theme options:
  - [x] Default theme (light)
  - [x] Dark theme
  - [x] Custom theme (forest-inspired)
- [x] Create a theme provider component
- [x] Add theme toggle functionality
- [x] Update components to use theme variables
- [x] Install necessary shadcn components (dropdown-menu, button)
- [x] Add theme toggle to header
- [x] Enhance forest theme with authentic rainforest colors (greens and browns)

## Why Multiple Themes Are Needed
Multiple themes enhance user experience by allowing users to choose their preferred visual style. This is particularly important for accessibility reasons (some users prefer dark mode to reduce eye strain) and for branding purposes (a forest-inspired theme aligns with our rainforest conservation project).

## Implementation Approach
We've used shadcn's recommended approach for theming, which involves:
1. CSS variables for color tokens in globals.css
2. A theme provider component using Next.js context
3. Local storage to persist user theme preferences

## Implementation Details
1. **Theme Provider**: Created a React context provider that manages theme state and persists it in localStorage
2. **Theme Toggle**: Added a dropdown menu in the header to switch between light, dark, and forest themes
3. **CSS Variables**: Added a new forest theme with green-focused colors to complement our rainforest conservation project
4. **Custom Variant**: Added a `forest` custom variant to support the new theme

## Forest Theme Color Palette
The forest theme uses a carefully selected palette of colors that evoke a rainforest environment:

- **Background**: Light cream color providing a neutral base
- **Foreground**: Dark brown text for good readability
- **Primary**: Deep forest green for primary actions and emphasis
- **Secondary**: Lighter green for secondary elements
- **Accent**: Earthy brown for accents and highlights
- **Destructive**: Reddish-brown reminiscent of fire (appropriate for a fire damage assessment platform)
- **Borders**: Medium brown for subtle separation
- **Sidebar**: Dark green for the sidebar with light cream text for contrast

Each color was chosen to create a cohesive, nature-inspired experience that reinforces the rainforest conservation theme of the application.

## Next Steps
- Test the theme toggle functionality across all pages
- Consider adding theme-specific imagery or accents to enhance the visual distinction between themes
- Ensure all components properly adapt to theme changes
