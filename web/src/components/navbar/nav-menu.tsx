import {
  NavigationMenu,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
} from "@/components/ui/navigation-menu";
import { NavigationMenuProps } from "@radix-ui/react-navigation-menu";
import Link from "next/link";

type NavMenuProps = NavigationMenuProps & {
  onItemClick?: () => void;
};

export const NavMenu = ({ onItemClick, ...props }: NavMenuProps) => (
  <NavigationMenu {...props}>
    <NavigationMenuList className="gap-6 space-x-0 data-[orientation=vertical]:flex-col-reverse data-[orientation=vertical]:items-center data-[orientation=vertical]:justify-center">
      <NavigationMenuItem>
        <NavigationMenuLink asChild>
          <Link href="#testimonials" onClick={onItemClick}>
            نظرات مشتریان
          </Link>
        </NavigationMenuLink>
      </NavigationMenuItem>

      <NavigationMenuItem>
        <NavigationMenuLink asChild>
          <Link href="#faq" onClick={onItemClick}>
            سوالات پرتکرار
          </Link>
        </NavigationMenuLink>
      </NavigationMenuItem>

      <NavigationMenuItem>
        <NavigationMenuLink asChild>
          <Link href="#pricing" onClick={onItemClick}>
            قیمت‌گذاری
          </Link>
        </NavigationMenuLink>
      </NavigationMenuItem>

      <NavigationMenuItem>
        <NavigationMenuLink asChild>
          <Link href="#features" onClick={onItemClick}>
            ویژگی‌ها
          </Link>
        </NavigationMenuLink>
      </NavigationMenuItem>
    </NavigationMenuList>
  </NavigationMenu>
);
