"use client";
import { Button } from "@/components/ui/button";
import { Logo } from "./logo";
import { NavMenu } from "./nav-menu";
import ThemeToggle from "../theme-toggle";
import { Spinner } from "@/components/ui/spinner";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Menu } from "lucide-react";

const Navbar = () => {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [sigloading, setsigLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

  const handleLoading = async () => {
    setLoading(true);
    requestAnimationFrame(() => {
      router.push("/login");
    });
    setTimeout(() => setLoading(false), 1500);
  };

  const handleSubmit = async () => {
    setsigLoading(true);
    requestAnimationFrame(() => {
      router.push("/signup");
    });
    setTimeout(() => setsigLoading(false), 1500);
  };

  const toggleMenu = () => {
    setIsOpen((prev) => !prev);
  };

  const handleNavClick = () => {
    setIsOpen(false);
  };

  return (
    <nav
      className={`fixed z-10 top-6 inset-x-4 bg-background/50 backdrop-blur-sm border dark:border-slate-700/70 max-w-screen-xl mx-auto rounded-3xl transition-all duration-500 overflow-hidden ${
        isOpen ? "h-auto py-4" : "h-14 xs:h-16"
      }`}
      dir="rtl"
    >
      <div className="flex flex-col lg:flex-row items-center mx-auto px-3 transition-all duration-300 h-full">
        <div className="w-full flex items-center justify-between h-full">
          <Logo />

          {/* Desktop Menu */}
          <NavMenu className="hidden lg:block" />

          <div className="flex items-center gap-3 ">
            <Button
              variant="outline"
              className="hidden sm:inline-flex rounded-full cursor-pointer"
              onClick={handleLoading}
              disabled={loading}
            >
              {loading ? <Spinner /> : "ورود"}
            </Button>
            <Button
              className="hidden sm:inline-flex rounded-full text-sm cursor-pointer"
              onClick={handleSubmit}
              disabled={sigloading}
            >
              {sigloading ? <Spinner /> : "ثبت نام در لیست انتظار"}
            </Button>

            {/* Mobile toggle */}
            <div className="lg:hidden">
              <Button
                variant="ghost"
                size="icon"
                className="rounded-full"
                onClick={toggleMenu}
              >
                <Menu className="w-5 h-5" />
              </Button>
            </div>
          </div>
        </div>

        {/* Mobile menu */}
        <div
          className={`lg:hidden w-full flex flex-col items-center gap-3 transition-all duration-300 ease-in-out ${
            isOpen
              ? "opacity-100 translate-y-0 max-h-[500px]"
              : "opacity-0 -translate-y-2 max-h-0 pointer-events-none"
          }`}
        >
          {/* منو موبایل که بعد از کلیک بسته میشه */}
          <NavMenu className="" orientation="vertical" onItemClick={handleNavClick} />

          <div className="flex gap-3 mt-5 md:hidden">
            <Button
              variant="outline"
              className="rounded-full flex-1 "
              onClick={handleLoading}
              disabled={loading}
            >
              {loading ? <Spinner /> : "ورود"}
            </Button>
            <Button className="rounded-full text-sm ">
              رایگان امتحان کنید
            </Button>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
