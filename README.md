# Metro Optimization Lab · ACO và QAOA

Website tương tác bằng tiếng Việt để tìm hiểu ACO cổ điển và thử QAOA cho bài toán người du lịch (TSP). QAOA là một phương pháp tối ưu lượng tử riêng, không phải ACO chạy bằng qubit; kết quả trên Qiskit Aer cục bộ không chứng minh tăng tốc lượng tử.

## Chạy website

Yêu cầu Python 3.10 trở lên. Cài các framework đã khóa phiên bản:

```powershell
python -m pip install -r requirements.txt
python app.py
```

Mở <http://127.0.0.1:8000>. Server chỉ bind vào loopback; dữ liệu thí nghiệm không gửi ra ngoài. Tắt server bằng `Ctrl+C`.

Website hỗ trợ 3–4 thành phố để giữ QAOA/Aer khả thi trên máy cục bộ. Có thể chọn bộ tọa độ mẫu hoặc nhập tọa độ riêng. Kết quả gồm tour ACO, tour QAOA nếu có mẫu khả thi, số mẫu tour khả thi được giải mã, số qubit, và thời gian CPU của hai lần chạy. QAOA có thể không sinh mẫu khả thi ở một lần chạy.

## Phương pháp

ACO xây tour từng bước, dùng pheromone `τ` và heuristic khoảng cách `η = 1/d`:

```text
w(i,j) = τ(i,j)^α · η(i,j)^β
P(i→j) = w(i,j) / Σ w(i,k)
```

Sau mỗi vòng, pheromone bay hơi và các tour gửi lượng tỉ lệ nghịch với độ dài; tour tốt nhất trong vòng được thưởng thêm. Bản demo dùng thêm nhánh chọn tham lam với `q0 = 0.8`.

QAOA biểu diễn TSP bằng biến nhị phân `x(i,t)`, với mỗi thành phố xuất hiện một lần và mỗi vị trí trong tour được gán một thành phố. Qiskit Optimization biến mô hình thành QuadraticProgram; QAOA dùng mạch tham số, Qiskit Aer sampler, và COBYLA để tối ưu các góc. `n` thành phố cần `n²` biến/qubit trong mã hóa này. Shots, độ sâu `p`, seed và số lần đánh giá COBYLA có thể điều chỉnh.

Hai thuật toán dùng pipeline và ngân sách tính toán khác nhau. Vì vậy không dùng thời gian simulator để kết luận về lợi thế tốc độ hay chất lượng tổng quát. Chỉ so sánh độ dài khi QAOA trả về tour hợp lệ.

## Các tệp chính

- `app.py`: server HTTP cục bộ và xác thực request thí nghiệm.
- `quantum_tsp.py`: giải TSP bằng QAOA trên Qiskit Aer và tạo kết quả so sánh.
- `aco_quantum.py`: ACO cổ điển cùng một heuristic quantum-inspired riêng. `QuantumInspiredAntColony` chỉ cập nhật xác suất bằng số thực trên CPU; nó không tạo mạch lượng tử và không được dùng thay QAOA trên website.
- `web/`: website, route map SVG tạo từ dữ liệu, và font có giấy phép đi kèm.

## Kiểm thử

```powershell
python -m unittest -v
```

## Tài liệu tham khảo

1. Dorigo, M., Maniezzo, V., & Colorni, A. (1996). “Ant system: optimization by a colony of cooperating agents.” *IEEE Transactions on Systems, Man, and Cybernetics, Part B*, 26(1), 29–41. [doi:10.1109/3477.484436](https://doi.org/10.1109/3477.484436)
2. Farhi, E., Goldstone, J., & Gutmann, S. (2014). “A Quantum Approximate Optimization Algorithm.” [arXiv:1411.4028](https://arxiv.org/abs/1411.4028)
3. Hadfield, S. et al. (2019). “From the Quantum Approximate Optimization Algorithm to a Quantum Alternating Operator Ansatz.” *Algorithms, 12*(2), 34. [doi:10.3390/a12020034](https://doi.org/10.3390/a12020034)
4. Qiskit Optimization, [Max-Cut and Traveling Salesman Problem](https://qiskit-community.github.io/qiskit-optimization/tutorials/06_examples_max_cut_and_tsp.html).
5. Qiskit Algorithms, [QAOA API documentation](https://qiskit-community.github.io/qiskit-algorithms/stubs/qiskit_algorithms.QAOA.html).
