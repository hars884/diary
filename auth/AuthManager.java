package auth;
import java.util.HashMap;
import java.util.Scanner;

public class AuthManager {
    private HashMap<String, String> users = new HashMap<>();

    public boolean register(String username, String password) {
        if (users.containsKey(username)) {
            System.out.println("User already exists!");
            return false;
        }
        users.put(username, password);
        System.out.println("User registered successfully!");
        return true;
    }

    public boolean login(String username, String password) {
        if (users.containsKey(username) && users.get(username).equals(password)) {
            System.out.println("Login successful!");
            return true;
        }
        System.out.println("Invalid username or password!");
        return false;
    }
}

