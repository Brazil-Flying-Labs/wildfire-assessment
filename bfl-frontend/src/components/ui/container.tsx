import { cn } from "@/lib/utils"
import { ReactNode, ElementType } from "react"

interface ContainerProps {
  className?: string
  children: ReactNode
  as?: ElementType
}

export function Container({
  className,
  children,
  as: Component = "div",
}: ContainerProps) {
  return (
    <Component
      className={cn(
        "mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8",
        className
      )}
    >
      {children}
    </Component>
  )
}
