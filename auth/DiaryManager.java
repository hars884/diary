package auth;
import java.util.ArrayList;
import java.util.List;

import diary.DiaryEntry;

public class DiaryManager {
    private List<DiaryEntry> entries = new ArrayList<>();

    public void addEntry(DiaryEntry entry) {
        entries.add(entry);
        System.out.println("Diary entry added successfully!");
    }

    public DiaryEntry searchByDate(String date) {
        for (DiaryEntry entry : entries) {
            if (entry.getDate().toString().equals(date)) {
                return entry;
            }
        }
        return null;
    }

    public List<DiaryEntry> getAllEntries() {
        return entries;
    }
}
