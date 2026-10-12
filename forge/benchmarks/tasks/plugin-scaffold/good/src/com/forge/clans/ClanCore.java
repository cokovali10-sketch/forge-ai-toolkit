package com.forge.clans;

import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.plugin.java.JavaPlugin;

public class ClanCore extends JavaPlugin implements Listener, CommandExecutor {
    @Override
    public void onEnable() {
        saveDefaultConfig();
        if (getCommand("clan") != null) {
            getCommand("clan").setExecutor(this);
        }
        getServer().getPluginManager().registerEvents(this, this);
        getLogger().info("ClanCore enabled (forge-generated)");
    }

    @EventHandler
    public void onJoin(PlayerJoinEvent e) {
        String msg = getConfig().getString("join-message", "");
        if (!msg.isEmpty()) {
            e.getPlayer().sendMessage(msg.replace("%player%", e.getPlayer().getName()));
        }
    }

    @Override
    public boolean onCommand(CommandSender sender, Command cmd, String label, String[] args) {
        if (!(sender instanceof Player player)) {
            sender.sendMessage("ClanCore console-ok");
            return true;
        }
        player.sendMessage(getConfig().getString("command-reply", "Hello from ClanCore!"));
        return true;
    }
}
