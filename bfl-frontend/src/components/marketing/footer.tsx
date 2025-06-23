import Link from 'next/link'
import { Facebook, Instagram, Linkedin, Twitter, Youtube, MapPin, Mail, Phone, Heart } from 'lucide-react'
import { Container } from '@/components/ui/container'
import Image from 'next/image'

export function Footer() {
  return (
    <footer className="bg-muted/30 border-t">
      <Container className="py-12 md:py-16">
        <div className="flex flex-col md:flex-row justify-between gap-8 mb-12">
          <div className="flex items-center gap-4 mb-6 md:mb-0">
            <div className="bg-background p-2 rounded-md shadow-sm">
              <Image
                src="/bfl-logo.jpeg"
                alt="Brazil Flying Labs Logo"
                width={60}
                height={60}
              />
            </div>
            <span className="text-primary font-medium text-xl">×</span>
            <div className="bg-background p-2 rounded-md shadow-sm">
              <Image
                src="/boone-voyage-logo.jpeg"
                alt="Boone Voyage Logo"
                width={60}
                height={60}
              />
            </div>
          </div>
          
          <div className="max-w-md">
            <h3 className="text-lg font-semibold mb-2">Our Collaboration</h3>
            <p className="text-muted-foreground mb-4">
              Brazil Flying Labs and Boone Voyage have joined forces to protect the Amazon rainforest through community-driven conservation, drone mapping, and reforestation initiatives.
            </p>
            <div className="flex space-x-4">
              <Link href="#" className="text-muted-foreground hover:text-foreground transition-colors">
                <Twitter className="h-5 w-5" />
                <span className="sr-only">Twitter</span>
              </Link>
              <Link href="#" className="text-muted-foreground hover:text-foreground transition-colors">
                <Facebook className="h-5 w-5" />
                <span className="sr-only">Facebook</span>
              </Link>
              <Link href="#" className="text-muted-foreground hover:text-foreground transition-colors">
                <Instagram className="h-5 w-5" />
                <span className="sr-only">Instagram</span>
              </Link>
              <Link href="#" className="text-muted-foreground hover:text-foreground transition-colors">
                <Linkedin className="h-5 w-5" />
                <span className="sr-only">LinkedIn</span>
              </Link>
              <Link href="#" className="text-muted-foreground hover:text-foreground transition-colors">
                <Youtube className="h-5 w-5" />
                <span className="sr-only">YouTube</span>
              </Link>
            </div>
          </div>
        </div>
        
        <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-4">
          <div>
            <h3 className="text-lg font-semibold mb-4">Our Work</h3>
            <ul className="space-y-3">
              <li>
                <Link href="#features" className="text-muted-foreground hover:text-foreground transition-colors">
                  Our Approach
                </Link>
              </li>
              <li>
                <Link href="#benefits" className="text-muted-foreground hover:text-foreground transition-colors">
                  Impact Stories
                </Link>
              </li>
              <li>
                <Link href="#how-it-works" className="text-muted-foreground hover:text-foreground transition-colors">
                  How We Collaborate
                </Link>
              </li>
              <li>
                <Link href="#" className="text-muted-foreground hover:text-foreground transition-colors">
                  Community Partners
                </Link>
              </li>
              <li>
                <Link href="#" className="text-muted-foreground hover:text-foreground transition-colors">
                  Research Publications
                </Link>
              </li>
            </ul>
          </div>
          
          <div>
            <h3 className="text-lg font-semibold mb-4">Get Involved</h3>
            <ul className="space-y-3">
              <li>
                <Link href="#support" className="text-muted-foreground hover:text-foreground transition-colors flex items-center gap-2">
                  <Heart className="h-4 w-4" /> Donate
                </Link>
              </li>
              <li>
                <Link href="#support" className="text-muted-foreground hover:text-foreground transition-colors">
                  Volunteer Opportunities
                </Link>
              </li>
              <li>
                <Link href="#support" className="text-muted-foreground hover:text-foreground transition-colors">
                  Corporate Partnerships
                </Link>
              </li>
              <li>
                <Link href="#support" className="text-muted-foreground hover:text-foreground transition-colors">
                  Educational Resources
                </Link>
              </li>
              <li>
                <Link href="#newsletter" className="text-muted-foreground hover:text-foreground transition-colors">
                  Newsletter
                </Link>
              </li>
            </ul>
          </div>
          
          <div>
            <h3 className="text-lg font-semibold mb-4">Brazil Flying Labs</h3>
            <ul className="space-y-3">
              <li className="flex items-start gap-2">
                <MapPin className="h-5 w-5 text-muted-foreground flex-shrink-0 mt-0.5" />
                <span className="text-muted-foreground">
                  Av. Paulista 1578, São Paulo, SP, Brazil
                </span>
              </li>
              <li className="flex items-start gap-2">
                <Mail className="h-5 w-5 text-muted-foreground flex-shrink-0 mt-0.5" />
                <Link href="mailto:contact@brazilflyinglabs.org" className="text-muted-foreground hover:text-foreground transition-colors">
                  contact@brazilflyinglabs.org
                </Link>
              </li>
              <li>
                <Link href="https://flyinglabs.org/brazil" className="text-muted-foreground hover:text-foreground transition-colors">
                  Visit Website
                </Link>
              </li>
            </ul>
          </div>
          
          <div>
            <h3 className="text-lg font-semibold mb-4">Boone Voyage</h3>
            <ul className="space-y-3">
              <li className="flex items-start gap-2">
                <MapPin className="h-5 w-5 text-muted-foreground flex-shrink-0 mt-0.5" />
                <span className="text-muted-foreground">
                  350 Mission Street, San Francisco, CA 94105, USA
                </span>
              </li>
              <li className="flex items-start gap-2">
                <Mail className="h-5 w-5 text-muted-foreground flex-shrink-0 mt-0.5" />
                <Link href="mailto:info@boonevoyage.org" className="text-muted-foreground hover:text-foreground transition-colors">
                  info@boonevoyage.org
                </Link>
              </li>
              <li className="flex items-start gap-2">
                <Phone className="h-5 w-5 text-muted-foreground flex-shrink-0 mt-0.5" />
                <Link href="tel:+14155551234" className="text-muted-foreground hover:text-foreground transition-colors">
                  +1 (415) 555-1234
                </Link>
              </li>
            </ul>
          </div>
        </div>
        
        <div className="mt-12 pt-8 border-t border-border flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="text-sm text-muted-foreground text-center md:text-left">
            <p>
              © {new Date().getFullYear()} Brazil Flying Labs & Boone Voyage. All rights reserved.
            </p>
            <p className="mt-1">
              Brazil Flying Labs is a registered 501(c)(3) non-profit organization.
            </p>
          </div>
          <div className="flex gap-6">
            <Link href="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Privacy Policy
            </Link>
            <Link href="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Terms of Service
            </Link>
            <Link href="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Cookie Policy
            </Link>
          </div>
        </div>
      </Container>
    </footer>
  )
}
