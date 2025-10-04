import { HTMLAttributes } from "react";
import { Logo } from "./navbar/logo";

function LogoCloud(props: HTMLAttributes<HTMLDivElement>) {
  return (
    <div {...props}>
      <h2 className="text-center text-3xl font-bold">یکپارچه‌سازی ساده با منابع دانش شما</h2>
      <div className="mt-3 flex flex-col items-center justify-center flex-wrap gap-4 [&_svg]:h-auto [&_svg]:w-24 xs:[&_svg]:w-auto xs:[&_svg]:h-8 text-muted-foreground">
        <div className="text-center">
          <p className="text-base">همه داده های آنلاین و آفلاین خود را به نکسا برای جستجو متصل کنید.</p>
        </div>
        <div>
          <div className="w-12 h-12">
            <img src="/Squad/image/card-img.png" alt="" />
          </div>
        </div>
      </div>
    </div>
  );
}

export default LogoCloud;
