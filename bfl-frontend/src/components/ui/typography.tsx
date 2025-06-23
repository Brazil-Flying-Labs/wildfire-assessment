import { cn } from "@/lib/utils"
import { ReactNode, ElementType } from "react"

interface TypographyProps {
  className?: string
  children: ReactNode
  as?: ElementType
}

export function H1({ className, children, as = "h1" }: TypographyProps) {
  const Component = as
  return (
    <Component
      className={cn(
        "scroll-m-20 text-4xl font-extrabold tracking-tight lg:text-5xl",
        className
      )}
    >
      {children}
    </Component>
  )
}

export function H2({ className, children, as = "h2" }: TypographyProps) {
  const Component = as
  return (
    <Component
      className={cn(
        "scroll-m-20 text-3xl font-semibold tracking-tight first:mt-0",
        className
      )}
    >
      {children}
    </Component>
  )
}

export function H3({ className, children, as = "h3" }: TypographyProps) {
  const Component = as
  return (
    <Component
      className={cn(
        "scroll-m-20 text-2xl font-semibold tracking-tight",
        className
      )}
    >
      {children}
    </Component>
  )
}

export function H4({ className, children, as = "h4" }: TypographyProps) {
  const Component = as
  return (
    <Component
      className={cn(
        "scroll-m-20 text-xl font-semibold tracking-tight",
        className
      )}
    >
      {children}
    </Component>
  )
}

export function P({ className, children, as = "p" }: TypographyProps) {
  const Component = as
  return (
    <Component
      className={cn("leading-7 [&:not(:first-child)]:mt-6", className)}
    >
      {children}
    </Component>
  )
}

export function Lead({ className, children, as = "p" }: TypographyProps) {
  const Component = as
  return (
    <Component
      className={cn("text-xl text-muted-foreground", className)}
    >
      {children}
    </Component>
  )
}

export function Large({ className, children, as = "div" }: TypographyProps) {
  const Component = as
  return (
    <Component
      className={cn("text-lg font-semibold", className)}
    >
      {children}
    </Component>
  )
}

export function Small({ className, children, as = "small" }: TypographyProps) {
  const Component = as
  return (
    <Component
      className={cn("text-sm font-medium leading-none", className)}
    >
      {children}
    </Component>
  )
}

export function Muted({ className, children, as = "p" }: TypographyProps) {
  const Component = as
  return (
    <Component
      className={cn("text-sm text-muted-foreground", className)}
    >
      {children}
    </Component>
  )
}
