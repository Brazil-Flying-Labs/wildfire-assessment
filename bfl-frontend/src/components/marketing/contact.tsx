import { Container } from '@/components/ui/container'
import Image from 'next/image'

export function Contact() {
  return (
    <section id="support" className="py-20 bg-muted/30">
      <Container>
        <div className="text-center mb-12">
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-4">
            Support Our Mission
          </h2>
          <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
            Join us in protecting the Amazon rainforest through our non-profit collaboration between Brazil Flying Labs and Boone Voyage.
          </p>
        </div>

        {/* Contact Form Section */}
        <div id="contact-form" className="bg-background rounded-lg border border-border overflow-hidden">
          <div className="grid md:grid-cols-2">
            <div className="p-8">
              <h3 className="text-xl font-semibold mb-6">Send Us a Message</h3>
              <form className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <label htmlFor="name" className="text-sm font-medium">
                      Name
                    </label>
                    <input
                      id="name"
                      type="text"
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                      placeholder="Your name"
                    />
                  </div>
                  <div className="space-y-2">
                    <label htmlFor="email" className="text-sm font-medium">
                      Email
                    </label>
                    <input
                      id="email"
                      type="email"
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                      placeholder="Your email"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <label htmlFor="interest" className="text-sm font-medium">
                    I&apos;m interested in
                  </label>
                  <select
                    id="interest"
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  >
                    <option value="">Select an option</option>
                    <option value="donate">Making a donation</option>
                    <option value="volunteer">Volunteering</option>
                    <option value="partner">Becoming a partner</option>
                    <option value="other">Other inquiry</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label htmlFor="message" className="text-sm font-medium">
                    Message
                  </label>
                  <textarea
                    id="message"
                    rows={4}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                    placeholder="Tell us how you'd like to get involved"
                  />
                </div>
                <button
                  type="submit"
                  className="inline-flex h-10 items-center justify-center rounded-full bg-primary px-6 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
                >
                  Send Message
                </button>
              </form>
            </div>
            <div className="relative bg-muted/50 flex items-center justify-center p-8">
              <div className="text-center">
                <div className="flex items-center justify-center gap-6 mb-6">
                  <div className="bg-background p-2 rounded-md shadow-sm">
                    <Image
                      src="/bfl-logo.jpeg"
                      alt="Brazil Flying Labs Logo"
                      width={80}
                      height={80}
                    />
                  </div>
                  <span className="text-primary font-medium text-xl">×</span>
                  <div className="bg-background p-2 rounded-md shadow-sm">
                    <Image
                      src="/boone-voyage-logo.jpeg"
                      alt="Boone Voyage Logo"
                      width={80}
                      height={80}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Container>
    </section>
  )
}
