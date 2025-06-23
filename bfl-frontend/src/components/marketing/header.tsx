'use client'

import Link from 'next/link'
import { useState } from 'react'
import { Container } from '@/components/ui/container'
import { ThemeToggle } from '@/components/theme-toggle'
import { Menu, X, Heart } from 'lucide-react'
import Image from 'next/image'

export function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/80 backdrop-blur-sm">
      <Container className="flex h-16 items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/" className="font-medium text-lg flex items-center gap-2">
            <div className="flex items-center gap-1">
              <span className="sr-only">Brazil Flying Labs and Boone Voyage</span>
              <div className="relative h-8 w-8">
                <Image 
                  src="/bfl-logo.jpeg" 
                  alt="Brazil Flying Labs Logo" 
                  fill 
                  className="object-contain"
                />
              </div>
              <span className="text-primary font-medium">×</span>
              <div className="relative h-8 w-8">
                <Image 
                  src="/boone-voyage-logo.jpeg" 
                  alt="Boone Voyage Logo" 
                  fill 
                  className="object-contain"
                />
              </div>
            </div>
            <span className="hidden sm:inline-block">MycorrhizAI</span>
          </Link>
        </div>
        
        <nav className="hidden md:flex items-center gap-6">
          <Link 
            href="#features" 
            className="text-sm font-medium transition-colors hover:text-primary"
          >
            Our Approach
          </Link>
          <Link 
            href="#benefits" 
            className="text-sm font-medium transition-colors hover:text-primary"
          >
            Impact Stories
          </Link>
          <Link 
            href="#how-it-works" 
            className="text-sm font-medium transition-colors hover:text-primary"
          >
            Our Collaboration
          </Link>
          <Link 
            href="#support" 
            className="text-sm font-medium transition-colors hover:text-primary"
          >
            Support Us
          </Link>
        </nav>
        <div className="hidden md:flex items-center gap-4">
          <ThemeToggle />
          <Link 
            href="/login" 
            className="rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 flex items-center gap-1"
          >
             Login
          </Link>
        </div>
        <button
          className="block md:hidden"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          aria-label="Toggle menu"
        >
          {mobileMenuOpen ? (
            <X className="h-6 w-6" />
          ) : (
            <Menu className="h-6 w-6" />
          )}
        </button>
      </Container>
      
      {/* Mobile menu */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-background border-b">
          <Container className="py-4 flex flex-col gap-4">
            <Link 
              href="#features" 
              className="text-sm font-medium transition-colors hover:text-primary py-2"
              onClick={() => setMobileMenuOpen(false)}
            >
              Our Approach
            </Link>
            <Link 
              href="#benefits" 
              className="text-sm font-medium transition-colors hover:text-primary py-2"
              onClick={() => setMobileMenuOpen(false)}
            >
              Impact Stories
            </Link>
            <Link 
              href="#how-it-works" 
              className="text-sm font-medium transition-colors hover:text-primary py-2"
              onClick={() => setMobileMenuOpen(false)}
            >
              Our Collaboration
            </Link>
            <Link 
              href="#support" 
              className="text-sm font-medium transition-colors hover:text-primary py-2"
              onClick={() => setMobileMenuOpen(false)}
            >
              Support Us
            </Link>
            <div className="flex items-center gap-4 pt-4 border-t mt-2">
              <ThemeToggle />
              <Link 
                href="/login" 
                className="text-sm font-medium transition-colors hover:text-primary"
                onClick={() => setMobileMenuOpen(false)}
              >
                Login
              </Link>
              <Link 
                href="#support" 
                className="rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 flex items-center gap-1"
                onClick={() => setMobileMenuOpen(false)}
              >
                <Heart className="h-4 w-4 mr-1" /> Donate
              </Link>
            </div>
          </Container>
        </div>
      )}
    </header>
  )
}
