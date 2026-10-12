package com.forge.labping;

import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.plugin.java.JavaPlugin;

public class LabPing extends JavaPlugin implements CommandExecutor {
    @Override
    public void onEnable() {
        if (getCommand("labping") != null) {
            getCommand("labping").setExecutor(this);
        }
        getLogger().info("LabPing enabled (forge fixture)");
    }

    @Override
    public boolean onCommand(CommandSender sender, Command cmd, String label, String[] args) {
        String arg = args.length > 0 ? String.join(" ", args) : "pong";
        sender.sendMessage("labpong " + arg);
        return true;
    }
}
