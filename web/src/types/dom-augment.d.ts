import 'react'

declare module 'react' {
  interface InputHTMLAttributes {
    webkitdirectory?: string
    directory?: string
  }
}

declare global {
  interface HTMLInputElement {
    webkitdirectory?: boolean
    directory?: boolean
  }
}