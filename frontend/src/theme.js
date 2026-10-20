import { createTheme } from '@mantine/core'

export const theme = createTheme({
  primaryColor: 'teal',
  primaryShade: 7,
  defaultRadius: 'sm',
  components: {
    Button: { defaultProps: { fw: 600 } },
    Modal: { defaultProps: { overlayProps: { backgroundOpacity: 0.4, blur: 2 } } },
    Drawer: { defaultProps: { overlayProps: { backgroundOpacity: 0.4, blur: 2 } } },
  },
})
