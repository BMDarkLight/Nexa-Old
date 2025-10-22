import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import {
  DribbbleIcon,
  GithubIcon,
  TwitchIcon,
  TwitterIcon,
} from "lucide-react";
import Link from "next/link";

const footerLinks = [
  {
    title: "ویژگی‌ها",
    href: "#features",
  },
  {
    title: "قیمت‌گذاری",
    href: "#pricing",
  },
  {
    title: "سوالات پرتکرار",
    href: "#faq",
  },
  {
    title: "نظرات مشتریان",
    href: "#testimonials",
  },
  {
    title: "قوانین و مقررات",
    href: "#privacy",
  },
];

const Footer = () => {
  return (
    <footer className="dark:border-t mt-40 dark bg-[#001120] text-foreground">
      <div className="max-w-screen-xl mx-auto">
        <div className="py-12 flex flex-col sm:flex-row items-start justify-between gap-x-8 gap-y-10 px-6 xl:px-0">
          <div>
            {/* Logo */}
            <div className="flex items-center">
              <div className="w-11 h-11">
                <img src="/Squad/Login/trans-logo.png" alt=""  />
              </div>
              <p className="text-lg">نکسا</p>
            </div>
            <ul className="mt-4 flex items-center gap-4 flex-wrap">
              {footerLinks.map(({ title, href }) => (
                <li key={title}>
                  <Link
                    href={href}
                    className="text-muted-foreground hover:text-foreground"
                  >
                    {title}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Subscribe Newsletter */}
          <div className="max-w-xs w-full">
            {/* <h6 className="font-semibold">Stay up to date</h6> */}
            <form className="mt-6 flex items-center justify-center gap-2 ">
              {/* <Input type="email" placeholder="Enter your email" /> */}
              <Button className=" rounded-full text-black bg-white">تماس با پشتیبانی و فروش</Button>
            </form>
          </div>
        </div>
        {/* <Separator /> */}
        <div className="py-8 flex flex-col-reverse sm:flex-row items-center justify-between gap-x-2 gap-y-5 px-6 xl:px-0">
          {/* Copyright */}
          <span className=" text-center sm:text-start">
             کلیه حقوق مادی و معنوی این وب‌سایت متعلق به تیم نکسا می‌باشد 
          </span>

          <div className="flex items-center gap-5 text-muted-foreground">
            <Link href="#" target="_blank">
              <img src="/Squad/image/Telegram.png" className="w-7 h-7" alt="" />
            </Link>
            <Link href="#" target="_blank">
              <img src="/Squad/image/gmail.png" className="w-7 h-7" alt="" />
            </Link>
            <Link href="#" target="_blank">
              <img src="/Squad/image/Linkdin.png" className="w-7 h-7" alt="" />
            </Link>
            <Link href="#" target="_blank">
              <img src="/Squad/image/instagram.png" className="w-7 h-7" alt="" />
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
