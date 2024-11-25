package application;
import java.time.LocalDate;
import java.util.Scanner;

import auth.AuthManager;
import auth.DiaryManager;
import diary.DiaryEntry;

public class AppBase {
    private AuthManager authManager = new AuthManager();
    private DiaryManager diaryManager = new DiaryManager();

    public void run() {
        Scanner scanner = new Scanner(System.in);
        while (true) {
            System.out.println("Welcome to Personal Diary");
            System.out.println("1. Register\n2. Login\n3. Exit");
            System.out.print("Choose an option: ");
            int choice = scanner.nextInt();
            scanner.nextLine(); // Consume newline

            switch (choice) {
                case 1 -> handleRegistration(scanner);
                case 2 -> handleLogin(scanner);
                case 3 -> {
                    System.out.println("Exiting application. Goodbye!");
                    return;
                }
                default -> System.out.println("Invalid option. Try again.");
            }
        }
    }

    private void handleRegistration(Scanner scanner) {
        System.out.print("Enter username: ");
        String username = scanner.nextLine();
        System.out.print("Enter password: ");
        String password = scanner.nextLine();
        authManager.register(username, password);
    }

    private void handleLogin(Scanner scanner) {
        System.out.print("Enter username: ");
        String username = scanner.nextLine();
        System.out.print("Enter password: ");
        String password = scanner.nextLine();

        if (authManager.login(username, password)) {
            userMenu(scanner);
        }
    }

    private void userMenu(Scanner scanner) {
        while (true) {
            System.out.println("1. Write Diary Entry\n2. View Diary Entry by Date\n3. View All Entries\n4. Logout");
            System.out.print("Choose an option: ");
            int choice = scanner.nextInt();
            scanner.nextLine(); // Consume newline

            switch (choice) {
                case 1 -> addDiaryEntry(scanner);
                case 2 -> viewDiaryEntryByDate(scanner);
                case 3 -> viewAllEntries();
                case 4 -> {
                    System.out.println("Logging out...");
                    return;
                }
                default -> System.out.println("Invalid option. Try again.");
            }
        }
    }

    private void addDiaryEntry(Scanner scanner) {
        System.out.print("Enter diary content: ");
        String content = scanner.nextLine();
        System.out.print("Enter emotion (Happy, Sad, Neutral): ");
        String emotion = scanner.nextLine();
        DiaryEntry entry = new DiaryEntry(LocalDate.now(), content, emotion);
        diaryManager.addEntry(entry);
    }

    private void viewDiaryEntryByDate(Scanner scanner) {
        System.out.print("Enter date (YYYY-MM-DD): ");
        String date = scanner.nextLine();
        DiaryEntry entry = diaryManager.searchByDate(date);
        if (entry != null) {
            System.out.println(entry);
        } else {
            System.out.println("No entry found for this date.");
        }
    }

    private void viewAllEntries() {
        System.out.println("All Diary Entries:");
        for (DiaryEntry entry : diaryManager.getAllEntries()) {
            System.out.println(entry);
            System.out.println("-------------------");
        }
    }
}