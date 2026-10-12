package com.mythic.shop;

import org.bukkit.Bukkit;
import org.bukkit.Material;
import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.inventory.InventoryClickEvent;
import org.bukkit.inventory.Inventory;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;
import org.bukkit.plugin.java.JavaPlugin;

import java.util.ArrayList;
import java.util.List;

/** Demo premium shop: categories, emerald prices, server-side buy logic. */
public class MythicShop extends JavaPlugin implements Listener, CommandExecutor {
    static final String TITLE = "Mythic Shop";

    @Override
    public void onEnable() {
        saveDefaultConfig();
        if (getCommand("mythicshop") != null) {
            getCommand("mythicshop").setExecutor(this);
        }
        Bukkit.getPluginManager().registerEvents(this, this);
        getLogger().info("MythicShop enabled (forge demo)");
    }

    @Override
    public boolean onCommand(CommandSender sender, Command cmd, String label, String[] args) {
        if (!(sender instanceof Player player)) {
            sender.sendMessage("mythicshop console-ok use-in-game-to-open");
            return true;
        }
        player.openInventory(buildGui());
        return true;
    }

    Inventory buildGui() {
        Inventory inv = Bukkit.createInventory(null, 27, TITLE);
        ItemStack filler = named(Material.GRAY_STAINED_GLASS_PANE, " ");
        for (int i = 0; i < 9; i++) {
            inv.setItem(i, filler);
        }
        inv.setItem(26, named(Material.BARRIER, "Close"));
        ConfigurationSection items = getConfig().getConfigurationSection("items");
        if (items != null) {
            for (String key : items.getKeys(false)) {
                int slot = items.getInt(key + ".slot", -1);
                if (slot < 9 || slot > 25) {
                    continue;
                }
                Material mat = Material.matchMaterial(items.getString(key + ".item", "STONE"));
                int price = items.getInt(key + ".price", 1);
                if (mat != null) {
                    inv.setItem(slot, named(mat, key + " - " + price + " emeralds"));
                }
            }
        }
        return inv;
    }

    @EventHandler
    public void onClick(InventoryClickEvent e) {
        if (!TITLE.equals(e.getView().getTitle())) {
            return;
        }
        e.setCancelled(true); // dupe-safe: nothing leaves by drag
        if (!(e.getWhoClicked() instanceof Player player)) {
            return;
        }
        ItemStack clicked = e.getCurrentItem();
        if (clicked == null || clicked.getType() == Material.GRAY_STAINED_GLASS_PANE) {
            return;
        }
        if (clicked.getType() == Material.BARRIER) {
            player.closeInventory();
            return;
        }
        ConfigurationSection items = getConfig().getConfigurationSection("items");
        if (items == null) {
            return;
        }
        for (String key : items.getKeys(false)) {
            if (items.getInt(key + ".slot", -1) != e.getRawSlot()) {
                continue;
            }
            Material mat = Material.matchMaterial(items.getString(key + ".item", ""));
            int price = items.getInt(key + ".price", 1);
            if (mat == null) {
                return;
            }
            if (!takeEmeralds(player, price)) {
                player.sendMessage("Not enough emeralds (" + price + " needed)");
                return;
            }
            player.getInventory().addItem(new ItemStack(mat, 1));
            player.sendMessage("Bought " + key + " for " + price + " emeralds");
            return;
        }
    }

    private boolean takeEmeralds(Player player, int price) {
        int found = 0;
        for (ItemStack s : player.getInventory().getContents()) {
            if (s != null && s.getType() == Material.EMERALD) {
                found += s.getAmount();
            }
        }
        if (found < price) {
            return false;
        }
        int left = price;
        for (ItemStack s : player.getInventory().getContents()) {
            if (left <= 0) {
                break;
            }
            if (s != null && s.getType() == Material.EMERALD) {
                int take = Math.min(left, s.getAmount());
                s.setAmount(s.getAmount() - take);
                left -= take;
            }
        }
        return true;
    }

    private static ItemStack named(Material mat, String name) {
        ItemStack s = new ItemStack(mat);
        ItemMeta meta = s.getItemMeta();
        if (meta != null) {
            meta.setDisplayName(name);
            List<String> lore = new ArrayList<>();
            lore.add("Mythic quality");
            meta.setLore(lore);
            s.setItemMeta(meta);
        }
        return s;
    }
}
