package diary;
import java.time.LocalDate;

public class DiaryEntry {
    private LocalDate date;
    private String content;
    private String emotion;

    public DiaryEntry(LocalDate date, String content, String emotion) {
        this.date = date;
        this.content = content;
        this.emotion = emotion;
    }

    public LocalDate getDate() {
        return date;
    }

    public String getContent() {
        return content;
    }

    public String getEmotion() {
        return emotion;
    }

    @Override
    public String toString() {
        return "Date: " + date + "\nEmotion: " + emotion + "\nContent:\n" + content;
    }
}
