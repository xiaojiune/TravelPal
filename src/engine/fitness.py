def analyze_solution(line, dis_matrix, spots_dict, travel_speed,
                     early_wait_weight=0.1,
                     penalty_weight=100.0,
                     late_return_weight=50.0,
                     depot=0):
    dis_sum = 0
    wait_penalty = 0
    late_penalty = 0
    depot_start = spots_dict[depot]["tw"][0]
    depot_end = spots_dict[depot]["tw"][1]
    current_time = depot_start
    violations = []

    for i in range(len(line) - 1):
        fr, to = line[i], line[i + 1]
        d = dis_matrix[fr][to]
        dis_sum += d
        travel_time = d / travel_speed
        arrival = current_time + travel_time

        if to != depot:
            start_t, end_t, stay = spots_dict[to]["tw"][0], spots_dict[to]["tw"][1], spots_dict[to]["stay"]
            if arrival < start_t:
                wait = start_t - arrival
                wait_penalty += wait * early_wait_weight
                current_time = start_t + stay
                violations.append((to, 'wait', wait))
            elif arrival > end_t:
                late = arrival - end_t
                late_penalty += late * penalty_weight
                current_time = arrival + stay
                violations.append((to, 'late', late))
            else:
                current_time = arrival + stay
        else:
            if arrival > depot_end:
                late_penalty += (arrival - depot_end) * late_return_weight
            current_time = arrival

    if current_time > depot_end:
        late_penalty += (current_time - depot_end) * late_return_weight

    total_penalty = wait_penalty + late_penalty
    total_cost = dis_sum + total_penalty
    return round(total_cost, 1), round(dis_sum, 1), round(wait_penalty, 1), round(late_penalty, 1), violations
