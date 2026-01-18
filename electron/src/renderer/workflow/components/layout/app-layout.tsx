import { cn } from "@/lib/utils"

interface AppLayoutProps {
  children: React.ReactNode
  className?: string
}

export function AppLayout({ children, className }: AppLayoutProps) {
  return (
    <div
      className={cn(
        "h-screen flex flex-col bg-background shadow-md overflow-hidden window",
        className
      )}
    >
      {children}
    </div>
  )
}

export function AppContent({ children, className }: AppLayoutProps) {
  return (
    <main className={cn("flex-1 min-h-0 overflow-hidden", className)}>
      {children}
    </main>
  )
}
