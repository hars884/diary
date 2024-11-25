package ui;

import javafx.application.Application;
import auth.AuthManager;
import auth.DiaryManager;
import diary.DiaryEntry;

import javafx.application.Application;
import javafx.geometry.Insets;
import javafx.scene.Scene;
import javafx.scene.control.*;
import javafx.scene.layout.*;
import javafx.stage.Stage;

import java.time.LocalDate;

public class DiaryAppUI extends Application {

    private AuthManager authManager = new AuthManager();
    private DiaryManager diaryManager = new DiaryManager();
    private String loggedInUser = null;

    @Override
    public void start(Stage primaryStage) {
        primaryStage.setTitle("Personal Diary");

        // Login Screen
        VBox loginLayout = new VBox(10);
        loginLayout.setPadding(new Insets(20));

        Label welcomeLabel = new Label("Welcome to Personal Diary");
        Label usernameLabel = new Label("Username:");
        TextField usernameField = new TextField();
        Label passwordLabel = new Label("Password:");
        PasswordField passwordField = new PasswordField();
        Button loginButton = new Button("Login");
        Button registerButton = new Button("Register");
        Label loginMessage = new Label();

        loginLayout.getChildren().addAll(
                welcomeLabel, usernameLabel, usernameField,
                passwordLabel, passwordField, loginButton, registerButton, loginMessage
        );

        Scene loginScene = new Scene(loginLayout, 400, 300);

        // Dashboard
        VBox dashboardLayout = new VBox(10);
        dashboardLayout.setPadding(new Insets(20));

        Label dashboardLabel = new Label("Diary Dashboard");
        Button writeEntryButton = new Button("Write New Entry");
        Button viewEntryButton = new Button("View Entry by Date");
        Button viewAllEntriesButton = new Button("View All Entries");
        Button logoutButton = new Button("Logout");

        dashboardLayout.getChildren().addAll(
                dashboardLabel, writeEntryButton, viewEntryButton, viewAllEntriesButton, logoutButton
        );

        Scene dashboardScene = new Scene(dashboardLayout, 400, 300);

        // Set Button Actions
        loginButton.setOnAction(e -> {
            String username = usernameField.getText();
            String password = passwordField.getText();

            if (authManager.login(username, password)) {
                loggedInUser = username;
                primaryStage.setScene(dashboardScene);
            } else {
                loginMessage.setText("Invalid username or password!");
            }
        });

        registerButton.setOnAction(e -> {
            String username = usernameField.getText();
            String password = passwordField.getText();

            if (authManager.register(username, password)) {
                loginMessage.setText("User registered successfully! You can now login.");
            } else {
                loginMessage.setText("User already exists!");
            }
        });

        logoutButton.setOnAction(e -> {
            loggedInUser = null;
            primaryStage.setScene(loginScene);
        });

        // Write Entry Screen
        VBox writeEntryLayout = new VBox(10);
        writeEntryLayout.setPadding(new Insets(20));

        Label entryLabel = new Label("Write a New Diary Entry");
        TextArea entryContentField = new TextArea();
        Label emotionLabel = new Label("Emotion:");
        ChoiceBox<String> emotionChoiceBox = new ChoiceBox<>();
        emotionChoiceBox.getItems().addAll("Happy", "Sad", "Neutral");
        Button saveEntryButton = new Button("Save Entry");
        Button backToDashboardButton1 = new Button("Back");

        writeEntryLayout.getChildren().addAll(
                entryLabel, entryContentField, emotionLabel, emotionChoiceBox, saveEntryButton, backToDashboardButton1
        );

        Scene writeEntryScene = new Scene(writeEntryLayout, 400, 300);

        writeEntryButton.setOnAction(e -> primaryStage.setScene(writeEntryScene));

        saveEntryButton.setOnAction(e -> {
            String content = entryContentField.getText();
            String emotion = emotionChoiceBox.getValue();

            if (content.isEmpty() || emotion == null) {
                entryLabel.setText("Please fill in all fields!");
            } else {
                DiaryEntry entry = new DiaryEntry(LocalDate.now(), content, emotion);
                diaryManager.addEntry(entry);
                entryLabel.setText("Entry saved successfully!");
                entryContentField.clear();
                emotionChoiceBox.getSelectionModel().clearSelection();
            }
        });

        backToDashboardButton1.setOnAction(e -> primaryStage.setScene(dashboardScene));

        // View Entries by Date Screen
        VBox viewEntryLayout = new VBox(10);
        viewEntryLayout.setPadding(new Insets(20));

        Label dateLabel = new Label("Enter Date (YYYY-MM-DD):");
        TextField dateField = new TextField();
        Button searchEntryButton = new Button("Search Entry");
        Label entryResultLabel = new Label();
        Button backToDashboardButton2 = new Button("Back");

        viewEntryLayout.getChildren().addAll(
                dateLabel, dateField, searchEntryButton, entryResultLabel, backToDashboardButton2
        );

        Scene viewEntryScene = new Scene(viewEntryLayout, 400, 300);

        viewEntryButton.setOnAction(e -> primaryStage.setScene(viewEntryScene));

        searchEntryButton.setOnAction(e -> {
            String date = dateField.getText();
            DiaryEntry entry = diaryManager.searchByDate(date);

            if (entry != null) {
                entryResultLabel.setText(entry.toString());
            } else {
                entryResultLabel.setText("No entry found for the specified date.");
            }
        });

        backToDashboardButton2.setOnAction(e -> primaryStage.setScene(dashboardScene));

        // Show Login Scene at Start
        primaryStage.setScene(loginScene);
        primaryStage.show();
    }
}

